"""NetherNet Network implementation using WebRTC.

Implements the Network interface for connecting to Minecraft Realms
via the NetherNet (NETHERNET_JSONRPC) protocol.
"""

from __future__ import annotations

import asyncio
import logging
import random

from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription

from mcbe.nethernet import aiortc_patch
aiortc_patch.apply()

from mcbe.nethernet.conn import NetherNetConn
from mcbe.nethernet.signaling import (
    SIGNAL_ANSWER,
    SIGNAL_CANDIDATE,
    SIGNAL_ERROR,
    SIGNAL_OFFER,
    JsonRpcSignaling,
    Signal,
    WebSocketSignaling,
    generate_network_id,
)
from mcbe.network import Network, NetworkConnection

logger = logging.getLogger(__name__)


def _prefer_tcp_turn(urls: list[str]) -> list[str]:
    """Rewrite TURN URLs to prefer TLS/TCP transport.

    Microsoft TURN servers (``relay.communication.microsoft.com``) often reject
    or drop UDP ALLOCATE requests.  aioice does not automatically fall back, so
    we synthesise ``turns:host:443?transport=tcp`` (TLS) from bare ``turn:``
    URLs and place them first.  aiortc only uses the **first** TURN server it
    encounters, so ordering matters.

    ``turns:`` URLs already present are kept as-is.
    ``stun:`` URLs are passed through unchanged.
    """
    import re
    out: list[str] = []
    has_turns = any(u.startswith("turns:") for u in urls)

    for url in urls:
        if url.startswith("turn:") and not url.startswith("turns:"):
            # Extract host from turn:host:port or turn:host
            m = re.match(r"^turn:([^:?]+)", url)
            if m and not has_turns:
                host = m.group(1)
                # Prepend a TURNS (TLS/TCP on 443) variant — most reliable path.
                out.insert(0, f"turns:{host}:443?transport=tcp")
                has_turns = True
            # Also add TCP variant of the original URL.
            if "?transport=" not in url and "transport=" not in url:
                out.append(url + "?transport=tcp")
            else:
                out.append(url)
        else:
            out.append(url)
    return out


class NetherNetNetwork(Network):
    """Network implementation using NetherNet (WebRTC) for Realms connections.

    Args:
        mc_token: MCToken authorization header from service authentication.
        network_id: Local network ID (typically XUID).
        signaling_url: WebSocket signaling server URL from Discovery API.
    """

    def __init__(self, mc_token: str, network_id: str = "", signaling_url: str = "", use_jsonrpc: bool = False) -> None:
        self._mc_token = mc_token
        self._network_id = network_id or generate_network_id()
        self._signaling_url = signaling_url
        self._use_jsonrpc = use_jsonrpc

    async def connect(self, address: str) -> NetworkConnection:
        """Connect to a remote NetherNet peer.

        Args:
            address: The remote network ID. May include a ``nethernet:``
                prefix which will be stripped automatically.

        Returns:
            A :class:`NetherNetConn` ready for packet I/O.
        """
        # Strip "nethernet:" prefix if present (Realms API may include it).
        if address.startswith("nethernet:"):
            address = address[len("nethernet:"):]
        logger.info("connecting to NetherNet peer: %s", address)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                return await self._try_connect(address)
            except ConnectionError as e:
                if "Player not found" in str(e) and attempt < max_retries - 1:
                    wait = 3 * (attempt + 1)
                    logger.info(
                        "peer not yet on signaling (attempt %d/%d), retrying in %ds...",
                        attempt + 1, max_retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise
        raise ConnectionError("failed to connect after retries")

    async def _try_connect(self, address: str) -> NetworkConnection:
        """Single connection attempt to a NetherNet peer."""
        kwargs = {}
        if self._signaling_url:
            kwargs["signaling_url"] = self._signaling_url
        if self._use_jsonrpc:
            signaling = JsonRpcSignaling(**kwargs)
        else:
            signaling = WebSocketSignaling(**kwargs)
        await signaling.connect(self._network_id, self._mc_token)

        try:
            # Wait for TURN/STUN credentials.
            creds = await signaling.credentials(timeout=10.0)
            logger.debug("received %d ICE servers", len(creds.ice_servers))

            # Build ICE server configuration.
            # aiortc/aioice often fails TURN ALLOCATE over UDP against Microsoft
            # relay servers.  Force TCP transport for TURN URLs so that relay
            # candidates are generated reliably.
            ice_servers = []
            for server in creds.ice_servers:
                urls = _prefer_tcp_turn(server.urls)
                logger.debug("ICE server: urls=%s", urls)
                ice_servers.append(RTCIceServer(
                    urls=urls,
                    username=server.username,
                    credential=server.password,
                ))

            config = RTCConfiguration(iceServers=ice_servers)
            pc = RTCPeerConnection(configuration=config)

            connection_id = random.getrandbits(64)

            # Create data channels (client side creates them).
            reliable_dc = pc.createDataChannel(
                "ReliableDataChannel",
                ordered=True,
            )
            unreliable_dc = pc.createDataChannel(
                "UnreliableDataChannel",
                ordered=False,
                maxRetransmits=0,
            )

            # Create and set local SDP offer.
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)

            # Wait for ICE gathering to complete.
            await _wait_ice_gathering(pc)

            # Send the offer via signaling.
            local_desc = pc.localDescription
            logger.info("SDP offer:\n%s", local_desc.sdp)
            await signaling.signal(Signal(
                type=SIGNAL_OFFER,
                connection_id=connection_id,
                data=local_desc.sdp,
                network_id=address,
            ))

            # Wait for answer from the remote peer.
            answer_received = False
            conn = NetherNetConn(pc, reliable_dc, unreliable_dc)

            while not answer_received:
                sig = await signaling.receive(timeout=30.0)

                # Filter for our connection.
                if sig.connection_id != connection_id:
                    continue

                if sig.type == SIGNAL_ANSWER:
                    # Set the remote description (SDP answer).
                    logger.info("SDP answer:\n%s", sig.data)
                    answer = RTCSessionDescription(sdp=sig.data, type="answer")
                    await pc.setRemoteDescription(answer)
                    answer_received = True
                    logger.info("received SDP answer from %s", sig.network_id)

                    # Diagnostic: log ICE internals
                    try:
                        for transport in pc._RTCPeerConnection__iceTransports:
                            ice_conn = transport._connection
                            logger.info(
                                "ICE check_list=%d protocols=%d remote_candidates=%d",
                                len(ice_conn._check_list),
                                len(ice_conn._protocols),
                                len(ice_conn._remote_candidates),
                            )
                            for i, pair in enumerate(ice_conn._check_list):
                                logger.info(
                                    "  pair[%d]: (%s:%d %s) -> (%s:%d %s) state=%s",
                                    i,
                                    pair.local_candidate.host, pair.local_candidate.port,
                                    pair.local_candidate.type,
                                    pair.remote_candidate.host, pair.remote_candidate.port,
                                    pair.remote_candidate.type,
                                    pair.state,
                                )
                    except Exception as e:
                        logger.warning("ICE diagnostic failed: %s", e)

                elif sig.type == SIGNAL_CANDIDATE:
                    # Add remote ICE candidate.
                    await _add_remote_candidate(pc, sig.data)

                elif sig.type == SIGNAL_ERROR:
                    raise ConnectionError(
                        f"remote peer signaled error (code: {sig.data})"
                    )

            # Continue receiving ICE candidates in background.
            asyncio.create_task(
                _handle_post_answer_signals(signaling, pc, connection_id, conn)
            )

            # Wait for reliable data channel to open.
            await _wait_datachannel_open(reliable_dc, timeout=30.0)
            logger.info("NetherNet connection established to %s", address)

            return conn

        except Exception:
            await signaling.close()
            raise

    async def ping(self, address: str) -> bytes:
        raise NotImplementedError("NetherNet does not support ping")

    async def listen(self, address: str):
        raise NotImplementedError("NetherNet listen not implemented")


async def _wait_ice_gathering(pc: RTCPeerConnection, timeout: float = 10.0) -> None:
    """Wait for ICE gathering to complete."""
    if pc.iceGatheringState == "complete":
        return

    event = asyncio.Event()
    original = pc.on

    @pc.on("icegatheringstatechange")
    def on_state_change():
        if pc.iceGatheringState == "complete":
            event.set()

    await asyncio.wait_for(event.wait(), timeout=timeout)


async def _wait_datachannel_open(dc, timeout: float = 30.0) -> None:
    """Wait for a DataChannel to enter the 'open' state."""
    if dc.readyState == "open":
        return

    event = asyncio.Event()

    @dc.on("open")
    def on_open():
        event.set()

    await asyncio.wait_for(event.wait(), timeout=timeout)


async def _add_remote_candidate(pc: RTCPeerConnection, candidate_str: str) -> None:
    """Parse and add a remote ICE candidate to the peer connection."""
    from aiortc import RTCIceCandidate

    candidate_str = candidate_str.strip()
    # Remove 'a=' prefix if present.
    if candidate_str.startswith("a="):
        candidate_str = candidate_str[2:]

    # aiortc expects addIceCandidate with an RTCIceCandidate object.
    # For now, we rely on candidates bundled in the SDP answer.
    # Individual candidate handling with aiortc is limited.
    logger.debug("remote ICE candidate: %s", candidate_str[:80])


async def _handle_post_answer_signals(
    signaling: WebSocketSignaling | JsonRpcSignaling,
    pc: RTCPeerConnection,
    connection_id: int,
    conn: NetherNetConn,
) -> None:
    """Background task: handle signals received after the SDP answer."""
    try:
        while True:
            try:
                sig = await signaling.receive(timeout=60.0)
            except asyncio.TimeoutError:
                continue

            if sig.connection_id != connection_id:
                continue

            if sig.type == SIGNAL_CANDIDATE:
                await _add_remote_candidate(pc, sig.data)
            elif sig.type == SIGNAL_ERROR:
                logger.warning("remote error signal: code=%s", sig.data)
                await conn.close()
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug("post-answer signal handler ended: %s", e)
    finally:
        await signaling.close()
