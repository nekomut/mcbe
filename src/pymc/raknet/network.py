"""RakNet network implementation.

Provides RakNetNetwork that implements the Network ABC using the
RakNet protocol over UDP for real Minecraft Bedrock Edition connections.
"""

from __future__ import annotations

import asyncio
import logging
import random
import struct
import time

from pymc.network import Network, NetworkConnection, NetworkListener
from pymc.raknet.connection import (
    RakNetClientConnection,
    RakNetClientProtocol,
    RakNetServerConnection,
    _current_time_ms,
)
from pymc.raknet.protocol import (
    DEFAULT_MTU,
    MAX_MTU,
    MIN_MTU,
    OPEN_CONNECTION_REPLY_1,
    OPEN_CONNECTION_REPLY_2,
    OPEN_CONNECTION_REQUEST_1,
    OPEN_CONNECTION_REQUEST_2,
    RAKNET_MAGIC,
    RAKNET_PROTOCOL_VERSION,
    UNCONNECTED_PING,
    UNCONNECTED_PONG,
    CONNECTION_REQUEST,
    read_address,
    write_address,
)

logger = logging.getLogger(__name__)


class RakNetNetwork(Network):
    """RakNet-based network transport for Minecraft Bedrock Edition."""

    def __init__(self, client_guid: int | None = None) -> None:
        self._client_guid = client_guid or random.randint(0, (1 << 63) - 1)

    async def connect(self, address: str) -> NetworkConnection:
        """Connect to a Minecraft Bedrock server via RakNet."""
        host, port_str = address.rsplit(":", 1)
        port = int(port_str)
        remote_addr = (host, port)

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            RakNetClientProtocol,
            remote_addr=None,
            local_addr=("0.0.0.0", 0),
        )

        # Get local address
        local_addr = transport.get_extra_info("sockname", ("0.0.0.0", 0))

        try:
            # Perform offline handshake
            mtu, server_guid = await self._offline_handshake(
                protocol, remote_addr
            )

            conn = RakNetClientConnection(
                protocol=protocol,
                remote_addr=remote_addr,
                local_addr=local_addr,
                mtu=mtu,
                client_guid=self._client_guid,
                server_guid=server_guid,
            )
            conn.start()

            # Send ConnectionRequest
            await self._send_connection_request(conn)

            return conn

        except Exception:
            transport.close()
            raise

    async def _offline_handshake(
        self,
        protocol: RakNetClientProtocol,
        remote_addr: tuple[str, int],
    ) -> tuple[int, int]:
        """Perform the RakNet offline handshake. Returns (mtu, server_guid)."""
        # Try MTU sizes from large to small
        mtu_sizes = [MAX_MTU, DEFAULT_MTU, MIN_MTU]
        server_guid = 0
        final_mtu = DEFAULT_MTU

        for mtu in mtu_sizes:
            # OpenConnectionRequest1: magic + protocol_version + MTU padding
            req1 = struct.pack("B", OPEN_CONNECTION_REQUEST_1)
            req1 += RAKNET_MAGIC
            req1 += struct.pack("B", RAKNET_PROTOCOL_VERSION)
            # Pad to MTU size (minus UDP header)
            padding_size = mtu - len(req1) - 28
            if padding_size > 0:
                req1 += b"\x00" * padding_size

            protocol.send(req1, remote_addr)

            try:
                data, addr = await protocol.recv(timeout=3.0)
            except asyncio.TimeoutError:
                logger.debug("MTU %d: no response, trying smaller", mtu)
                continue

            if data[0] != OPEN_CONNECTION_REPLY_1:
                logger.debug("Unexpected reply to request 1: 0x%02x", data[0])
                continue

            # Parse OpenConnectionReply1:
            # packet_id(1) + magic(16) + server_guid(8) + use_security(1) + mtu(2)
            offset = 1 + 16  # skip id + magic
            server_guid = struct.unpack(">q", data[offset:offset + 8])[0]
            offset += 8
            use_security = data[offset]
            offset += 1
            final_mtu = struct.unpack(">H", data[offset:offset + 2])[0]
            break
        else:
            raise ConnectionError("Failed RakNet MTU negotiation")

        # OpenConnectionRequest2: magic + server_address + mtu + client_guid
        req2 = struct.pack("B", OPEN_CONNECTION_REQUEST_2)
        req2 += RAKNET_MAGIC
        req2 += write_address(remote_addr[0], remote_addr[1])
        req2 += struct.pack(">H", final_mtu)
        req2 += struct.pack(">q", self._client_guid)

        protocol.send(req2, remote_addr)

        data, addr = await protocol.recv(timeout=5.0)
        if data[0] != OPEN_CONNECTION_REPLY_2:
            raise ConnectionError(
                f"Expected OpenConnectionReply2, got 0x{data[0]:02x}"
            )

        # Parse OpenConnectionReply2:
        # packet_id(1) + magic(16) + server_guid(8) + client_address + mtu(2) + encryption(1)
        offset = 1 + 16  # skip id + magic
        server_guid = struct.unpack(">q", data[offset:offset + 8])[0]
        offset += 8
        _host, _port, offset = read_address(data, offset)
        final_mtu = struct.unpack(">H", data[offset:offset + 2])[0]

        logger.info("RakNet handshake complete: MTU=%d, server_guid=%d", final_mtu, server_guid)
        return final_mtu, server_guid

    async def _send_connection_request(self, conn: RakNetClientConnection) -> None:
        """Send the online ConnectionRequest packet."""
        payload = struct.pack("B", CONNECTION_REQUEST)
        payload += struct.pack(">q", conn._client_guid)
        payload += struct.pack(">q", _current_time_ms())
        payload += b"\x00"  # use_security = false
        conn._send_frame(payload)

    async def ping(self, address: str) -> bytes:
        """Ping a Minecraft Bedrock server and return pong data."""
        host, port_str = address.rsplit(":", 1)
        port = int(port_str)
        remote_addr = (host, port)

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            RakNetClientProtocol,
            remote_addr=None,
            local_addr=("0.0.0.0", 0),
        )

        try:
            # UnconnectedPing: id + time(8) + magic + client_guid(8)
            ping = struct.pack("B", UNCONNECTED_PING)
            ping += struct.pack(">q", _current_time_ms())
            ping += RAKNET_MAGIC
            ping += struct.pack(">q", self._client_guid)

            protocol.send(ping, remote_addr)

            data, addr = await protocol.recv(timeout=5.0)
            if data[0] != UNCONNECTED_PONG:
                raise ConnectionError(
                    f"Expected UnconnectedPong, got 0x{data[0]:02x}"
                )

            # Parse UnconnectedPong:
            # id(1) + time(8) + server_guid(8) + magic(16) + string_length(2) + string
            offset = 1 + 8 + 8 + 16
            str_len = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            pong_data = data[offset:offset + str_len]
            return pong_data

        finally:
            transport.close()

    async def listen(self, address: str) -> NetworkListener:
        """Start listening for RakNet connections."""
        host, port_str = address.rsplit(":", 1)
        port = int(port_str)

        loop = asyncio.get_running_loop()
        listener = RakNetListener(server_guid=self._client_guid)

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: listener._protocol,
            local_addr=(host, port),
        )
        listener._transport = transport
        listener.start()

        return listener


class _RakNetServerProtocol(asyncio.DatagramProtocol):
    """Server-side UDP protocol that dispatches to the listener."""

    def __init__(self, listener: RakNetListener) -> None:
        self._listener = listener
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._listener._handle_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        logger.error("Server UDP error: %s", exc)


class RakNetListener(NetworkListener):
    """RakNet server listener that accepts incoming connections."""

    def __init__(self, server_guid: int = 0) -> None:
        self._server_guid = server_guid or random.randint(0, (1 << 63) - 1)
        self._protocol = _RakNetServerProtocol(self)
        self._transport: asyncio.DatagramTransport | None = None
        self._pong_data: bytes = b""
        self._connections: dict[tuple[str, int], RakNetServerConnection] = {}
        self._pending: dict[tuple[str, int], int] = {}  # addr -> mtu (during handshake)
        self._accept_queue: asyncio.Queue[RakNetServerConnection] = asyncio.Queue()
        self._closed = False
        self._tick_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._tick_task = asyncio.create_task(self._tick_loop())

    async def _tick_loop(self) -> None:
        try:
            while not self._closed:
                await asyncio.sleep(0.05)
                for conn in list(self._connections.values()):
                    conn.flush_acks()
        except asyncio.CancelledError:
            pass

    def _handle_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        """Route incoming datagrams to the appropriate handler."""
        if not data:
            return
        packet_id = data[0]

        # Check if this is from an established connection
        conn = self._connections.get(addr)
        if conn is not None:
            conn.handle_datagram(data)
            return

        # Offline packets
        if packet_id == UNCONNECTED_PING or packet_id == 0x02:
            self._handle_ping(data, addr)
        elif packet_id == OPEN_CONNECTION_REQUEST_1:
            self._handle_open_request_1(data, addr)
        elif packet_id == OPEN_CONNECTION_REQUEST_2:
            self._handle_open_request_2(data, addr)

    def _handle_ping(self, data: bytes, addr: tuple[str, int]) -> None:
        """Respond to an unconnected ping."""
        if not self._transport:
            return
        offset = 1
        ping_time = struct.unpack(">q", data[offset:offset + 8])[0]

        pong = struct.pack("B", UNCONNECTED_PONG)
        pong += struct.pack(">q", ping_time)
        pong += struct.pack(">q", self._server_guid)
        pong += RAKNET_MAGIC
        pong += struct.pack(">H", len(self._pong_data))
        pong += self._pong_data
        self._transport.sendto(pong, addr)

    def _handle_open_request_1(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle OpenConnectionRequest1."""
        if not self._transport:
            return
        # Calculate MTU from packet size
        mtu = len(data) + 28  # add UDP header
        if mtu > MAX_MTU:
            mtu = MAX_MTU
        if mtu < MIN_MTU:
            mtu = MIN_MTU
        self._pending[addr] = mtu

        reply = struct.pack("B", OPEN_CONNECTION_REPLY_1)
        reply += RAKNET_MAGIC
        reply += struct.pack(">q", self._server_guid)
        reply += b"\x00"  # use_security = false
        reply += struct.pack(">H", mtu)
        self._transport.sendto(reply, addr)

    def _handle_open_request_2(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle OpenConnectionRequest2 and create server connection."""
        if not self._transport:
            return
        mtu = self._pending.pop(addr, DEFAULT_MTU)

        # Parse: id(1) + magic(16) + server_address + mtu(2) + client_guid(8)
        offset = 1 + 16
        _host, _port, offset = read_address(data, offset)
        client_mtu = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        client_guid = struct.unpack(">q", data[offset:offset + 8])[0]

        final_mtu = min(mtu, client_mtu)

        # Send OpenConnectionReply2
        reply = struct.pack("B", OPEN_CONNECTION_REPLY_2)
        reply += RAKNET_MAGIC
        reply += struct.pack(">q", self._server_guid)
        reply += write_address(addr[0], addr[1])
        reply += struct.pack(">H", final_mtu)
        reply += b"\x00"  # encryption_enabled = false
        self._transport.sendto(reply, addr)

        # Create server connection
        conn = RakNetServerConnection(
            transport=self._transport,
            client_addr=addr,
            mtu=final_mtu,
            server_guid=self._server_guid,
        )
        self._connections[addr] = conn
        self._accept_queue.put_nowait(conn)

    # ── NetworkListener interface ───────────────────────────────

    async def accept(self) -> NetworkConnection:
        return await self._accept_queue.get()

    def set_pong_data(self, data: bytes) -> None:
        self._pong_data = data

    def server_id(self) -> int:
        return self._server_guid

    async def close(self) -> None:
        self._closed = True
        if self._tick_task:
            self._tick_task.cancel()
        for conn in self._connections.values():
            await conn.close()
        if self._transport:
            self._transport.close()
