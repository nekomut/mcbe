"""RakNet connection handling.

Provides async RakNet client and server connections built on asyncio
DatagramProtocol. Handles frame sets, ACK/NACK, reliability, ordering,
and fragment reassembly.
"""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from dataclasses import dataclass, field

from pymc.network import NetworkConnection
from pymc.raknet.protocol import (
    ACK,
    CONNECTED_PING,
    CONNECTED_PONG,
    CONNECTION_REQUEST,
    CONNECTION_REQUEST_ACCEPTED,
    DEFAULT_MTU,
    DISCONNECTION_NOTIFICATION,
    FRAME_SET_MAX,
    FRAME_SET_MIN,
    GAME_PACKET,
    NACK,
    NEW_INCOMING_CONNECTION,
    OPEN_CONNECTION_REPLY_1,
    OPEN_CONNECTION_REPLY_2,
    OPEN_CONNECTION_REQUEST_1,
    OPEN_CONNECTION_REQUEST_2,
    RAKNET_MAGIC,
    RAKNET_PROTOCOL_VERSION,
    RELIABLE_ORDERED,
    RELIABLE_TYPES,
    UNCONNECTED_PING,
    UNCONNECTED_PONG,
    Frame,
    decode_ack_nack,
    decode_frame_set,
    encode_ack,
    encode_frame_set,
    encode_nack,
    read_address,
    write_address,
    write_uint24le,
)

logger = logging.getLogger(__name__)

# Frame overhead: flags(1) + length(2) + reliable_index(3) + ordered_index(3) + order_channel(1) = 10
FRAME_OVERHEAD = 10
# Frame set header: packet_id(1) + sequence_number(3) = 4
FRAME_SET_HEADER = 4
# UDP+IP overhead
UDP_HEADER_SIZE = 28


@dataclass
class _FragmentBuffer:
    """Buffer for reassembling fragmented frames."""

    compound_size: int
    fragments: dict[int, bytes] = field(default_factory=dict)

    def add(self, index: int, data: bytes) -> bytes | None:
        """Add a fragment. Returns reassembled data when complete, else None."""
        self.fragments[index] = data
        if len(self.fragments) == self.compound_size:
            return b"".join(self.fragments[i] for i in range(self.compound_size))
        return None


class RakNetClientProtocol(asyncio.DatagramProtocol):
    """Async UDP protocol for RakNet client communication."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._recv_queue: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue()
        self._connected = asyncio.Event()
        self._error: Exception | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._recv_queue.put_nowait((data, addr))

    def error_received(self, exc: Exception) -> None:
        self._error = exc

    def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            self._error = exc

    def send(self, data: bytes, addr: tuple[str, int]) -> None:
        if self.transport:
            self.transport.sendto(data, addr)

    async def recv(self, timeout: float = 5.0) -> tuple[bytes, tuple[str, int]]:
        return await asyncio.wait_for(self._recv_queue.get(), timeout=timeout)


class RakNetClientConnection(NetworkConnection):
    """RakNet client connection implementing the NetworkConnection ABC.

    Handles the full RakNet connection lifecycle including offline handshake,
    online connection, reliability layer, and game packet extraction.
    """

    def __init__(
        self,
        protocol: RakNetClientProtocol,
        remote_addr: tuple[str, int],
        local_addr: tuple[str, int],
        mtu: int = DEFAULT_MTU,
        client_guid: int = 0,
        server_guid: int = 0,
    ) -> None:
        self._protocol = protocol
        self._remote_addr = remote_addr
        self._local_addr = local_addr
        self._mtu = mtu
        self._client_guid = client_guid
        self._server_guid = server_guid
        self._closed = False

        # Sending state
        self._send_seq: int = 0
        self._reliable_index: int = 0
        self._ordered_index: int = 0
        self._compound_id: int = 0

        # Receiving state
        self._expected_seq: int = 0
        self._ack_queue: list[int] = []
        self._nack_queue: list[int] = []

        # Recovery (for resending on NACK)
        self._recovery: dict[int, bytes] = {}

        # Fragment reassembly
        self._fragments: dict[int, _FragmentBuffer] = {}

        # Ordered packet queue
        self._ordered_queue: dict[int, bytes] = {}
        self._ordered_read_index: int = 0

        # Game packet queue (ready for application to consume)
        self._game_packets: asyncio.Queue[bytes] = asyncio.Queue()

        # Online handshake completion event
        self._connected = asyncio.Event()

        # Background tasks
        self._recv_task: asyncio.Task[None] | None = None
        self._tick_task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start background receive and tick loops."""
        self._recv_task = asyncio.create_task(self._recv_loop())
        self._tick_task = asyncio.create_task(self._tick_loop())

    async def _recv_loop(self) -> None:
        """Background loop processing incoming datagrams."""
        try:
            while not self._closed:
                try:
                    data, addr = await asyncio.wait_for(
                        self._protocol._recv_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                if addr != self._remote_addr:
                    continue
                await self._handle_datagram(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("RakNet recv loop error: %s", e)

    async def _tick_loop(self) -> None:
        """Background loop sending ACKs and pings."""
        try:
            while not self._closed:
                await asyncio.sleep(0.05)  # 50ms tick
                self._flush_acks()
        except asyncio.CancelledError:
            pass

    def _flush_acks(self) -> None:
        """Send queued ACKs and NACKs."""
        if self._ack_queue:
            data = encode_ack(self._ack_queue)
            self._protocol.send(data, self._remote_addr)
            self._ack_queue.clear()
        if self._nack_queue:
            data = encode_nack(self._nack_queue)
            self._protocol.send(data, self._remote_addr)
            self._nack_queue.clear()

    async def _handle_datagram(self, data: bytes) -> None:
        """Route an incoming datagram to the appropriate handler."""
        if not data:
            return
        packet_id = data[0]

        if packet_id == ACK:
            self._handle_ack(data)
        elif packet_id == NACK:
            self._handle_nack(data)
        elif FRAME_SET_MIN <= packet_id <= FRAME_SET_MAX:
            self._handle_frame_set(data)
        else:
            logger.debug("Unknown RakNet packet: 0x%02x", packet_id)

    def _handle_ack(self, data: bytes) -> None:
        """Process ACK: remove from recovery queue."""
        for seq in decode_ack_nack(data):
            self._recovery.pop(seq, None)

    def _handle_nack(self, data: bytes) -> None:
        """Process NACK: resend from recovery queue."""
        for seq in decode_ack_nack(data):
            if seq in self._recovery:
                self._protocol.send(self._recovery[seq], self._remote_addr)

    def _handle_frame_set(self, data: bytes) -> None:
        """Process a frame set packet."""
        seq_num, frames = decode_frame_set(data)

        # Track for ACK
        self._ack_queue.append(seq_num)

        # Detect gaps for NACK
        while self._expected_seq < seq_num:
            self._nack_queue.append(self._expected_seq)
            self._expected_seq += 1
        if seq_num >= self._expected_seq:
            self._expected_seq = seq_num + 1

        for frame in frames:
            self._handle_frame(frame)

    def _handle_frame(self, frame: Frame) -> None:
        """Process a single frame, handling fragmentation and ordering."""
        if frame.fragmented:
            buf = self._fragments.get(frame.compound_id)
            if buf is None:
                buf = _FragmentBuffer(compound_size=frame.compound_size)
                self._fragments[frame.compound_id] = buf
            reassembled = buf.add(frame.fragment_index, frame.body)
            if reassembled is not None:
                del self._fragments[frame.compound_id]
                self._process_payload(reassembled)
            return

        self._process_payload(frame.body)

    def _process_payload(self, data: bytes) -> None:
        """Process a complete payload (after reassembly)."""
        if not data:
            return
        packet_id = data[0]

        if packet_id == CONNECTED_PING:
            self._handle_connected_ping(data)
        elif packet_id == CONNECTED_PONG:
            pass  # Ignore pong responses
        elif packet_id == DISCONNECTION_NOTIFICATION:
            logger.info("Server sent disconnect notification")
            self._closed = True
        elif packet_id == GAME_PACKET:
            # Pass full data including 0xFE header for decode_batch
            self._game_packets.put_nowait(data)
        elif packet_id == CONNECTION_REQUEST_ACCEPTED:
            self._handle_connection_accepted(data)

    def _handle_connected_ping(self, data: bytes) -> None:
        """Respond to a connected ping with a connected pong."""
        if len(data) >= 9:
            ping_time = struct.unpack(">q", data[1:9])[0]
            pong = struct.pack("B", CONNECTED_PONG) + struct.pack(">q", ping_time) + struct.pack(">q", _current_time_ms())
            self._send_frame(pong)

    def _handle_connection_accepted(self, data: bytes) -> None:
        """Handle ConnectionRequestAccepted and send NewIncomingConnection."""
        offset = 1
        # Read server address
        _host, _port, offset = read_address(data, offset)
        # Read system index (short)
        offset += 2
        # Read system addresses (up to 20)
        for _ in range(20):
            if offset >= len(data) - 16:
                break
            try:
                _, _, offset = read_address(data, offset)
            except Exception:
                break
        # Send NewIncomingConnection
        payload = struct.pack("B", NEW_INCOMING_CONNECTION)
        payload += write_address(self._remote_addr[0], self._remote_addr[1])
        # System addresses (fill with empty)
        for _ in range(20):
            payload += write_address("0.0.0.0", 0)
        payload += struct.pack(">q", _current_time_ms())
        payload += struct.pack(">q", _current_time_ms())
        self._send_frame(payload)
        self._connected.set()

    def _send_frame(self, data: bytes, reliability: int = RELIABLE_ORDERED) -> None:
        """Send data as a reliable ordered frame."""
        max_body = self._mtu - UDP_HEADER_SIZE - FRAME_SET_HEADER - FRAME_OVERHEAD
        if len(data) > max_body:
            self._send_fragmented(data, reliability, max_body)
            return

        frame = Frame(
            reliability=reliability,
            body=data,
            reliable_index=self._next_reliable_index(),
            ordered_index=self._next_ordered_index(),
            order_channel=0,
        )
        self._send_frame_set([frame])

    def _send_fragmented(self, data: bytes, reliability: int, max_body: int) -> None:
        """Split data into fragments and send."""
        compound_id = self._compound_id
        self._compound_id = (self._compound_id + 1) & 0xFFFF

        # Account for fragment header overhead
        frag_overhead = 4 + 2 + 4  # compound_size + compound_id + index
        frag_body = max_body - frag_overhead
        if frag_body <= 0:
            frag_body = max_body

        chunks = [data[i:i + frag_body] for i in range(0, len(data), frag_body)]
        compound_size = len(chunks)

        for i, chunk in enumerate(chunks):
            frame = Frame(
                reliability=reliability,
                body=chunk,
                reliable_index=self._next_reliable_index(),
                ordered_index=self._next_ordered_index() if i == 0 else self._ordered_index - 1,
                order_channel=0,
                fragmented=True,
                compound_size=compound_size,
                compound_id=compound_id,
                fragment_index=i,
            )
            self._send_frame_set([frame])

    def _send_frame_set(self, frames: list[Frame]) -> None:
        """Encode and send a frame set."""
        seq = self._send_seq
        self._send_seq += 1
        data = encode_frame_set(seq, frames)
        self._recovery[seq] = data
        self._protocol.send(data, self._remote_addr)

    def _next_reliable_index(self) -> int:
        idx = self._reliable_index
        self._reliable_index += 1
        return idx

    def _next_ordered_index(self) -> int:
        idx = self._ordered_index
        self._ordered_index += 1
        return idx

    # ── NetworkConnection interface ─────────────────────────────

    async def read_packet(self) -> bytes:
        """Read a game packet (0xFE payload, after the 0xFE byte is stripped)."""
        if self._closed:
            raise ConnectionError("Connection is closed")
        return await self._game_packets.get()

    async def write_packet(self, data: bytes) -> None:
        """Write a game packet. Data must already start with 0xFE batch header."""
        if self._closed:
            raise ConnectionError("Connection is closed")
        self._send_frame(data)

    async def close(self) -> None:
        """Close the connection."""
        if self._closed:
            return
        self._closed = True
        # Send disconnect
        self._send_frame(struct.pack("B", DISCONNECTION_NOTIFICATION))
        self._flush_acks()
        # Cancel background tasks
        if self._recv_task:
            self._recv_task.cancel()
        if self._tick_task:
            self._tick_task.cancel()
        if self._protocol.transport:
            self._protocol.transport.close()


class RakNetServerConnection(NetworkConnection):
    """RakNet server-side connection for an accepted client.

    Manages the reliability layer for a single client connected
    to a RakNet server listener.
    """

    def __init__(
        self,
        transport: asyncio.DatagramTransport,
        client_addr: tuple[str, int],
        mtu: int = DEFAULT_MTU,
        server_guid: int = 0,
    ) -> None:
        self._transport = transport
        self._client_addr = client_addr
        self._mtu = mtu
        self._server_guid = server_guid
        self._closed = False

        # Sending state
        self._send_seq: int = 0
        self._reliable_index: int = 0
        self._ordered_index: int = 0
        self._compound_id: int = 0

        # Receiving state
        self._expected_seq: int = 0
        self._ack_queue: list[int] = []
        self._nack_queue: list[int] = []

        # Recovery
        self._recovery: dict[int, bytes] = {}

        # Fragment reassembly
        self._fragments: dict[int, _FragmentBuffer] = {}

        # Game packet queue
        self._game_packets: asyncio.Queue[bytes] = asyncio.Queue()

    def handle_datagram(self, data: bytes) -> None:
        """Handle incoming datagram from the client (called by listener)."""
        if not data:
            return
        packet_id = data[0]

        if packet_id == ACK:
            for seq in decode_ack_nack(data):
                self._recovery.pop(seq, None)
        elif packet_id == NACK:
            for seq in decode_ack_nack(data):
                if seq in self._recovery:
                    self._transport.sendto(self._recovery[seq], self._client_addr)
        elif FRAME_SET_MIN <= packet_id <= FRAME_SET_MAX:
            seq_num, frames = decode_frame_set(data)
            self._ack_queue.append(seq_num)
            while self._expected_seq < seq_num:
                self._nack_queue.append(self._expected_seq)
                self._expected_seq += 1
            if seq_num >= self._expected_seq:
                self._expected_seq = seq_num + 1
            for frame in frames:
                self._handle_frame(frame)

    def _handle_frame(self, frame: Frame) -> None:
        if frame.fragmented:
            buf = self._fragments.get(frame.compound_id)
            if buf is None:
                buf = _FragmentBuffer(compound_size=frame.compound_size)
                self._fragments[frame.compound_id] = buf
            reassembled = buf.add(frame.fragment_index, frame.body)
            if reassembled is not None:
                del self._fragments[frame.compound_id]
                self._process_payload(reassembled)
            return
        self._process_payload(frame.body)

    def _process_payload(self, data: bytes) -> None:
        if not data:
            return
        packet_id = data[0]
        if packet_id == CONNECTED_PING:
            if len(data) >= 9:
                ping_time = struct.unpack(">q", data[1:9])[0]
                pong = struct.pack("B", CONNECTED_PONG) + struct.pack(">q", ping_time) + struct.pack(">q", _current_time_ms())
                self._send_frame(pong)
        elif packet_id == CONNECTION_REQUEST:
            self._handle_connection_request(data)
        elif packet_id == NEW_INCOMING_CONNECTION:
            logger.debug("Client sent NewIncomingConnection")
        elif packet_id == DISCONNECTION_NOTIFICATION:
            self._closed = True
        elif packet_id == GAME_PACKET:
            # Pass full data including 0xFE header for decode_batch
            self._game_packets.put_nowait(data)

    def _handle_connection_request(self, data: bytes) -> None:
        """Handle ConnectionRequest and send ConnectionRequestAccepted."""
        offset = 1
        client_guid = struct.unpack(">q", data[offset:offset + 8])[0]
        offset += 8
        request_time = struct.unpack(">q", data[offset:offset + 8])[0]
        offset += 8
        # use_security byte (skip)

        # Send ConnectionRequestAccepted
        payload = struct.pack("B", CONNECTION_REQUEST_ACCEPTED)
        payload += write_address(self._client_addr[0], self._client_addr[1])
        payload += struct.pack(">H", 0)  # system index
        for _ in range(20):
            payload += write_address("0.0.0.0", 0)
        payload += struct.pack(">q", request_time)
        payload += struct.pack(">q", _current_time_ms())
        self._send_frame(payload)

    def flush_acks(self) -> None:
        """Flush queued ACKs/NACKs."""
        if self._ack_queue:
            data = encode_ack(self._ack_queue)
            self._transport.sendto(data, self._client_addr)
            self._ack_queue.clear()
        if self._nack_queue:
            data = encode_nack(self._nack_queue)
            self._transport.sendto(data, self._client_addr)
            self._nack_queue.clear()

    def _send_frame(self, data: bytes, reliability: int = RELIABLE_ORDERED) -> None:
        max_body = self._mtu - UDP_HEADER_SIZE - FRAME_SET_HEADER - FRAME_OVERHEAD
        if len(data) > max_body:
            self._send_fragmented(data, reliability, max_body)
            return
        frame = Frame(
            reliability=reliability,
            body=data,
            reliable_index=self._next_reliable_index(),
            ordered_index=self._next_ordered_index(),
            order_channel=0,
        )
        self._send_frame_set([frame])

    def _send_fragmented(self, data: bytes, reliability: int, max_body: int) -> None:
        compound_id = self._compound_id
        self._compound_id = (self._compound_id + 1) & 0xFFFF
        frag_overhead = 4 + 2 + 4
        frag_body = max_body - frag_overhead
        if frag_body <= 0:
            frag_body = max_body
        chunks = [data[i:i + frag_body] for i in range(0, len(data), frag_body)]
        compound_size = len(chunks)
        for i, chunk in enumerate(chunks):
            frame = Frame(
                reliability=reliability,
                body=chunk,
                reliable_index=self._next_reliable_index(),
                ordered_index=self._next_ordered_index() if i == 0 else self._ordered_index - 1,
                order_channel=0,
                fragmented=True,
                compound_size=compound_size,
                compound_id=compound_id,
                fragment_index=i,
            )
            self._send_frame_set([frame])

    def _send_frame_set(self, frames: list[Frame]) -> None:
        seq = self._send_seq
        self._send_seq += 1
        data = encode_frame_set(seq, frames)
        self._recovery[seq] = data
        self._transport.sendto(data, self._client_addr)

    def _next_reliable_index(self) -> int:
        idx = self._reliable_index
        self._reliable_index += 1
        return idx

    def _next_ordered_index(self) -> int:
        idx = self._ordered_index
        self._ordered_index += 1
        return idx

    # ── NetworkConnection interface ─────────────────────────────

    async def read_packet(self) -> bytes:
        if self._closed:
            raise ConnectionError("Connection is closed")
        return await self._game_packets.get()

    async def write_packet(self, data: bytes) -> None:
        if self._closed:
            raise ConnectionError("Connection is closed")
        self._send_frame(data)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._send_frame(struct.pack("B", DISCONNECTION_NOTIFICATION))
        self.flush_acks()


def _current_time_ms() -> int:
    """Return current time in milliseconds."""
    return int(time.time() * 1000)
