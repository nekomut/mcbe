"""WebSocket signaling client for NetherNet.

Handles SDP offer/answer and ICE candidate exchange via the Minecraft
signaling WebSocket server.

Two signaling protocols are supported:

1. **Legacy (Type-based)** — ``WebSocketSignaling``
   Message types (from bedrock-tool/franchise/signaling/message.go):
     0 = Ping (client→server) / Error (server→client, From="Server")
     1 = Signal (bidirectional, contains "{TYPE} {ConnectionID} {Data}")
     2 = Credentials (server→client, TURN/STUN info, From="Server")

2. **JSON-RPC 2.0** — ``JsonRpcSignaling``
   Used when the Realms API returns ``NETHERNET_JSONRPC`` as network protocol.
   Methods: Signaling_TurnAuth_v1_0, Signaling_SendClientMessage_v1_0,
   Signaling_ReceiveMessage_v1_0, System_Ping_v1_0, etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from dataclasses import dataclass, field

import websockets

logger = logging.getLogger(__name__)

# Default signaling URL (overridden by Discovery API).
DEFAULT_SIGNALING_URL = "wss://signal.franchise.minecraft-services.net"
SIGNALING_PATH = "/ws/v1.0/signaling/{network_id}"

# WebSocket message types.
MSG_TYPE_PING = 0  # Also Error (From != "")
MSG_TYPE_SIGNAL = 1
MSG_TYPE_CREDENTIALS = 2
MSG_TYPE_ACK = 3  # Message delivery acknowledgement

# Signal types matching go-nethernet signal.go constants.
SIGNAL_OFFER = "CONNECTREQUEST"
SIGNAL_ANSWER = "CONNECTRESPONSE"
SIGNAL_CANDIDATE = "CANDIDATEADD"
SIGNAL_ERROR = "CONNECTERROR"

# Keepalive interval in seconds.
PING_INTERVAL = 15.0


def generate_network_id() -> str:
    """Generate a random network ID (uint64 as string)."""
    return str(random.getrandbits(64))


@dataclass
class Credentials:
    """TURN/STUN server credentials received from the signaling server."""

    expiration_in_seconds: int = 0
    ice_servers: list[ICEServer] = field(default_factory=list)


@dataclass
class ICEServer:
    """A single ICE server configuration."""

    username: str = ""
    password: str = ""
    urls: list[str] = field(default_factory=list)


@dataclass
class Signal:
    """A signaling message exchanged between peers."""

    type: str = ""
    connection_id: int = 0
    data: str = ""
    network_id: str = ""

    def encode(self) -> str:
        """Encode as the wire format: ``{TYPE} {ConnectionID} {Data}``."""
        return f"{self.type} {self.connection_id} {self.data}"

    @classmethod
    def decode(cls, text: str, network_id: str = "") -> Signal:
        """Decode from the wire format."""
        parts = text.split(" ", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid signal format: {text!r}")
        return cls(
            type=parts[0],
            connection_id=int(parts[1]),
            data=parts[2],
            network_id=network_id,
        )


class WebSocketSignaling:
    """WebSocket signaling client for NetherNet connections.

    Connects to the Minecraft signaling server and exchanges signals
    (SDP offers/answers and ICE candidates) with remote peers.
    """

    def __init__(self, signaling_url: str = DEFAULT_SIGNALING_URL) -> None:
        self._signaling_url = signaling_url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._network_id: str = ""
        self._credentials_future: asyncio.Future[Credentials] | None = None
        self._signal_queue: asyncio.Queue[Signal] = asyncio.Queue()
        self._error_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._closed = False

    @property
    def network_id(self) -> str:
        return self._network_id

    async def connect(self, network_id: str, mc_token: str) -> None:
        """Connect to the signaling server.

        Args:
            network_id: The local network ID (random uint64 as string).
            mc_token: The MCToken authorization header value.
        """
        self._network_id = network_id
        self._credentials_future = asyncio.get_event_loop().create_future()

        path = SIGNALING_PATH.format(network_id=network_id)
        url = self._signaling_url + path
        logger.info("signaling URL: %s", url)
        self._ws = await websockets.connect(
            url,
            additional_headers={"Authorization": mc_token},
            ping_interval=None,  # We handle our own keepalive.
        )
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.debug("signaling connected: network_id=%s", network_id)

    async def credentials(self, timeout: float = 10.0) -> Credentials:
        """Wait for and return TURN/STUN credentials from the server."""
        if self._credentials_future is None:
            raise RuntimeError("Not connected")
        return await asyncio.wait_for(self._credentials_future, timeout=timeout)

    async def signal(self, sig: Signal) -> None:
        """Send a signal to a remote network."""
        if self._ws is None:
            raise RuntimeError("Not connected")
        # To field: uint64 for numeric IDs, string for UUIDs.
        try:
            to_val: int | str = int(sig.network_id)
        except (ValueError, TypeError):
            to_val = sig.network_id
        msg = {
            "Type": MSG_TYPE_SIGNAL,
            "To": to_val,
            "Message": sig.encode(),
        }
        raw = json.dumps(msg)
        logger.info("signaling send: %s", raw[:300])
        await self._ws.send(raw)

    async def receive(self, timeout: float = 30.0) -> Signal:
        """Receive the next signal from the queue.

        Raises :class:`ConnectionError` if a signaling error is received
        before a signal arrives.
        """
        signal_task = asyncio.ensure_future(self._signal_queue.get())
        error_task = asyncio.ensure_future(self._error_queue.get())
        try:
            done, pending = await asyncio.wait(
                {signal_task, error_task},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

            if not done:
                raise TimeoutError("signaling receive timed out")

            if error_task in done:
                err = error_task.result()
                raise ConnectionError(
                    f"signaling error: {err.get('Message', err)}"
                )
            return signal_task.result()
        except asyncio.CancelledError:
            signal_task.cancel()
            error_task.cancel()
            raise

    async def close(self) -> None:
        """Close the signaling connection."""
        self._closed = True
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()

    async def _recv_loop(self) -> None:
        """Background task: receive and dispatch WebSocket messages."""
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    raw = raw.decode()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("invalid JSON from signaling: %s", raw[:200])
                    continue

                msg_type = msg.get("Type", -1)
                logger.info("signaling recv: type=%d from=%s msg=%s",
                            msg_type, msg.get("From", ""), str(msg.get("Message", ""))[:200])

                if msg_type == MSG_TYPE_CREDENTIALS:
                    # Credentials from server (TURN/STUN info).
                    try:
                        cred_data = msg.get("Message", "{}")
                        if isinstance(cred_data, str):
                            cred_data = json.loads(cred_data)
                        creds = _parse_credentials(cred_data)
                        if self._credentials_future and not self._credentials_future.done():
                            self._credentials_future.set_result(creds)
                        logger.info("received credentials: %d ICE servers", len(creds.ice_servers))
                    except Exception as e:
                        logger.warning("failed to parse credentials: %s", e)

                elif msg_type == MSG_TYPE_SIGNAL:
                    # Signal from a remote peer.
                    from_id = msg.get("From", "")
                    message = msg.get("Message", "")
                    try:
                        sig = Signal.decode(message, network_id=from_id)
                        await self._signal_queue.put(sig)
                        logger.info("received signal: type=%s from=%s conn=%d", sig.type, from_id, sig.connection_id)
                    except ValueError as e:
                        logger.warning("invalid signal message: %s", e)

                elif msg_type == MSG_TYPE_PING:
                    # Type 0: Ping response (no From) or Error (From != "").
                    from_id = msg.get("From", "")
                    if from_id:
                        # Error from server or from target peer.
                        raw_msg = msg.get("Message", "")
                        try:
                            err_data = json.loads(raw_msg) if isinstance(raw_msg, str) else raw_msg
                        except (json.JSONDecodeError, TypeError):
                            err_data = {"Message": raw_msg}
                        err_data["From"] = from_id
                        await self._error_queue.put(err_data)
                        logger.warning("signaling error from %s: %s", from_id, err_data)

                elif msg_type == MSG_TYPE_ACK:
                    # Delivery acknowledgement — informational.
                    pass

                else:
                    logger.warning("unknown signaling message type=%d: %s", msg_type, str(msg)[:300])

        except websockets.ConnectionClosed as e:
            if not self._closed:
                logger.warning("signaling WebSocket closed unexpectedly: %s", e)
        except asyncio.CancelledError:
            pass

    async def _ping_loop(self) -> None:
        """Background task: send keepalive pings every 15 seconds."""
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL)
                if self._ws:
                    await self._ws.send(json.dumps({"Type": MSG_TYPE_PING}))
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass


def _parse_credentials(data: dict) -> Credentials:
    """Parse credentials JSON from the signaling server.

    Supports both PascalCase (legacy) and camelCase (JSON-RPC) field names.
    """
    servers = []
    turn_servers = data.get("TurnAuthServers") or data.get("turnAuthServers", [])
    for s in turn_servers:
        servers.append(ICEServer(
            username=s.get("Username") or s.get("username", ""),
            password=s.get("Password") or s.get("password") or s.get("Credential") or s.get("credential", ""),
            urls=s.get("Urls") or s.get("urls", []),
        ))
    return Credentials(
        expiration_in_seconds=data.get("ExpirationInSeconds") or data.get("expirationInSeconds", 0),
        ice_servers=servers,
    )


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 signaling (NETHERNET_JSONRPC)
# ---------------------------------------------------------------------------

JSONRPC_PATH = "/ws/v1.0/messaging/connect"
JSONRPC_PING_DELAY = 30.0
JSONRPC_PING_INTERVAL = 50.0


class JsonRpcSignaling:
    """JSON-RPC 2.0 signaling client for NetherNet connections.

    Used when the Realms server advertises the ``NETHERNET_JSONRPC`` protocol.
    """

    def __init__(self, signaling_url: str = DEFAULT_SIGNALING_URL) -> None:
        self._signaling_url = signaling_url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._network_id: str = ""
        self._credentials_future: asyncio.Future[Credentials] | None = None
        self._signal_queue: asyncio.Queue[Signal] = asyncio.Queue()
        self._error_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._closed = False
        self._pending: dict[str, asyncio.Future] = {}

    @property
    def network_id(self) -> str:
        return self._network_id

    async def connect(self, network_id: str, mc_token: str) -> None:
        """Connect to the JSON-RPC signaling server and request TURN credentials."""
        self._network_id = network_id
        self._credentials_future = asyncio.get_event_loop().create_future()

        url = self._signaling_url + JSONRPC_PATH
        logger.info("signaling URL: %s", url)
        self._ws = await websockets.connect(
            url,
            additional_headers={"Authorization": mc_token},
            ping_interval=None,
        )
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.debug("JSON-RPC signaling connected: network_id=%s", network_id)

        # Request TURN credentials via RPC.
        asyncio.create_task(self._request_turn_auth())

    async def _request_turn_auth(self) -> None:
        """Send Signaling_TurnAuth_v1_0 and resolve credentials."""
        try:
            result = await self._rpc_call("Signaling_TurnAuth_v1_0", {})
            creds = _parse_credentials(result)
            if self._credentials_future and not self._credentials_future.done():
                self._credentials_future.set_result(creds)
            logger.info("received credentials: %d ICE servers", len(creds.ice_servers))
        except Exception as e:
            logger.warning("failed to get TURN auth: %s", e)
            if self._credentials_future and not self._credentials_future.done():
                self._credentials_future.set_exception(e)

    async def credentials(self, timeout: float = 10.0) -> Credentials:
        """Wait for and return TURN/STUN credentials from the server."""
        if self._credentials_future is None:
            raise RuntimeError("Not connected")
        return await asyncio.wait_for(self._credentials_future, timeout=timeout)

    async def signal(self, sig: Signal) -> None:
        """Send a signal to a remote network via JSON-RPC."""
        if self._ws is None:
            raise RuntimeError("Not connected")

        # Inner message: Signaling_WebRtc_v1_0
        inner = json.dumps({
            "jsonrpc": "2.0",
            "method": "Signaling_WebRtc_v1_0",
            "params": {
                "netherNetId": self._network_id,
                "message": sig.encode(),
            },
        })

        message_id = str(uuid.uuid4())

        # Outer: Signaling_SendClientMessage_v1_0
        await self._rpc_call("Signaling_SendClientMessage_v1_0", {
            "toPlayerId": sig.network_id,
            "messageId": message_id,
            "message": inner,
        })

    async def receive(self, timeout: float = 30.0) -> Signal:
        """Receive the next signal from the queue.

        Raises :class:`ConnectionError` if a signaling error is received
        before a signal arrives.
        """
        signal_task = asyncio.ensure_future(self._signal_queue.get())
        error_task = asyncio.ensure_future(self._error_queue.get())
        try:
            done, pending = await asyncio.wait(
                {signal_task, error_task},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()

            if not done:
                raise TimeoutError("signaling receive timed out")

            if error_task in done:
                err = error_task.result()
                raise ConnectionError(
                    f"signaling error: {err.get('Message') or err.get('message', err)}"
                )
            return signal_task.result()
        except asyncio.CancelledError:
            signal_task.cancel()
            error_task.cancel()
            raise

    async def close(self) -> None:
        """Close the signaling connection."""
        self._closed = True
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        for fut in self._pending.values():
            fut.cancel()
        self._pending.clear()
        if self._ws:
            await self._ws.close()

    # -- RPC helpers --

    async def _rpc_call(self, method: str, params: dict) -> dict:
        """Send a JSON-RPC request and wait for the response."""
        if self._ws is None:
            raise RuntimeError("Not connected")
        req_id = str(uuid.uuid4())
        future: asyncio.Future[dict] = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id,
        }
        raw = json.dumps(msg)
        logger.info("signaling rpc send: method=%s id=%s", method, req_id[:8])
        await self._ws.send(raw)
        return await future

    async def _rpc_notify(self, method: str, params: dict) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        if self._ws is None:
            return
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        await self._ws.send(json.dumps(msg))

    async def _rpc_respond(self, req_id, result=None) -> None:
        """Send a JSON-RPC response to a server request."""
        if self._ws is None:
            return
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }
        await self._ws.send(json.dumps(msg))

    # -- Background tasks --

    async def _recv_loop(self) -> None:
        """Background task: receive and dispatch JSON-RPC messages."""
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    raw = raw.decode()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("invalid JSON from signaling: %s", raw[:200])
                    continue

                logger.debug("signaling rpc recv: %s", raw[:500])

                if "method" in msg:
                    # Server-initiated request or notification.
                    await self._handle_server_request(msg)
                elif "result" in msg or "error" in msg:
                    # Response to our RPC call.
                    self._handle_rpc_response(msg)
                else:
                    logger.warning("unknown JSON-RPC message: %s", raw[:300])

        except websockets.ConnectionClosed as e:
            if not self._closed:
                logger.warning("signaling WebSocket closed unexpectedly: %s", e)
        except asyncio.CancelledError:
            pass

    async def _handle_server_request(self, msg: dict) -> None:
        """Handle an incoming JSON-RPC request from the server."""
        method = msg.get("method", "")
        params = msg.get("params", {})
        req_id = msg.get("id")

        if method == "Signaling_ReceiveMessage_v1_0":
            # Acknowledge to server first.
            if req_id is not None:
                await self._rpc_respond(req_id)
            # Process messages and send delivery notifications back to peers.
            await self._handle_receive_message(params)

        elif method == "System_Ping_v1_0":
            if req_id is not None:
                await self._rpc_respond(req_id)

        else:
            logger.debug("unhandled server RPC method: %s", method)
            if req_id is not None:
                await self._rpc_respond(req_id)

    async def _handle_receive_message(self, params) -> None:
        """Extract signals from a Signaling_ReceiveMessage_v1_0 notification."""
        if isinstance(params, list):
            messages = params
        elif isinstance(params, dict):
            messages = [params]
        else:
            logger.warning("unexpected params type: %s", type(params))
            return

        for entry in messages:
            if not isinstance(entry, dict):
                continue

            # Support both camelCase and PascalCase field names.
            mid = entry.get("messageId") or entry.get("Id") or entry.get("id", "")
            sender_id = entry.get("fromPlayerId") or entry.get("From") or entry.get("from", "")
            raw_message = entry.get("message") or entry.get("Message") or ""
            logger.info("signaling rpc receive: from=%s msg=%s", sender_id, str(raw_message)[:200])

            # Send delivery notification back to the sender via SendClientMessage.
            # Use create_task to avoid blocking the recv_loop (deadlock).
            if mid and sender_id:
                asyncio.create_task(self._send_delivery_notification(sender_id, mid))

            # Parse the inner message.
            try:
                inner = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
            except (json.JSONDecodeError, TypeError):
                logger.warning("failed to parse inner message: %s", str(raw_message)[:200])
                continue

            if not isinstance(inner, dict):
                continue

            # Check for server error messages (e.g. delivery failures).
            if "Code" in inner or "code" in inner:
                code = inner.get("Code") or inner.get("code", 0)
                err_msg = inner.get("Message") or inner.get("message", "")
                logger.warning("signaling error from %s: code=%s msg=%s", sender_id, code, err_msg)
                await self._error_queue.put({"Message": err_msg, "Code": code, "From": sender_id})
                continue

            inner_method = inner.get("method", "")
            inner_params = inner.get("params", {})

            if inner_method == "Signaling_WebRtc_v1_0":
                network_id = inner_params.get("netherNetId", sender_id)
                payload = inner_params.get("message", "")
                try:
                    sig = Signal.decode(payload, network_id=network_id)
                    await self._signal_queue.put(sig)
                    logger.info("received signal: type=%s from=%s conn=%d",
                                sig.type, network_id, sig.connection_id)
                except ValueError as e:
                    logger.warning("invalid signal in RPC message: %s", e)
            elif inner_method == "Signaling_DeliveryNotification_V1_0":
                logger.debug("delivery notification from %s", sender_id)
            else:
                logger.debug("unhandled inner method: %s", inner_method)

    async def _send_delivery_notification(self, sender_id: str, message_id: str) -> None:
        """Send a delivery notification back to the sender."""
        try:
            dn_inner = json.dumps({
                "jsonrpc": "2.0",
                "method": "Signaling_DeliveryNotification_V1_0",
                "params": {"messageId": message_id},
            })
            await self._rpc_call("Signaling_SendClientMessage_v1_0", {
                "toPlayerId": sender_id,
                "messageId": str(uuid.uuid4()),
                "message": dn_inner,
            })
        except Exception as e:
            logger.debug("failed to send delivery notification: %s", e)

    def _handle_rpc_response(self, msg: dict) -> None:
        """Resolve a pending RPC future with the response."""
        req_id = msg.get("id", "")
        future = self._pending.pop(req_id, None)
        if future is None:
            logger.debug("received response for unknown id: %s", req_id)
            return

        if "error" in msg:
            err = msg["error"]
            err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            future.set_exception(ConnectionError(f"RPC error: {err_msg}"))
        else:
            future.set_result(msg.get("result", {}))

    async def _ping_loop(self) -> None:
        """Background task: send System_Ping_v1_0 every 50 seconds."""
        try:
            await asyncio.sleep(JSONRPC_PING_DELAY)
            while True:
                try:
                    await self._rpc_call("System_Ping_v1_0", {})
                except Exception:
                    pass
                await asyncio.sleep(JSONRPC_PING_INTERVAL)
        except (asyncio.CancelledError, websockets.ConnectionClosed):
            pass
