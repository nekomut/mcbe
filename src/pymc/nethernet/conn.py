"""NetherNet connection over WebRTC DataChannel.

Implements the NetworkConnection interface using aiortc's DataChannel
with packet segmentation matching go-nethernet's wire format.
"""

from __future__ import annotations

import asyncio
import logging
import math

from pymc.network import NetworkConnection

logger = logging.getLogger(__name__)

# Maximum payload per segment (excluding the 1-byte header).
MAX_MESSAGE_SIZE = 10_000

# Maximum number of segments (uint8 range: 0-255, so 256 segments).
MAX_SEGMENTS = math.floor(math.pow(2, 8))


class NetherNetConn(NetworkConnection):
    """A Minecraft connection over a WebRTC DataChannel.

    Handles segmentation/reassembly of packets using the NetherNet
    wire format: each segment is ``[remaining: uint8][payload]``.

    Attributes:
        pc: The aiortc RTCPeerConnection.
        reliable_dc: The ordered ReliableDataChannel.
        unreliable_dc: The unordered UnreliableDataChannel (may be None).
    """

    def __init__(
        self,
        pc: object,
        reliable_dc: object,
        unreliable_dc: object | None = None,
    ) -> None:
        self._pc = pc
        self._reliable_dc = reliable_dc
        self._unreliable_dc = unreliable_dc

        # Incoming packet queue (fully reassembled).
        self._packets: asyncio.Queue[bytes] = asyncio.Queue()

        # Reassembly state for the reliable channel.
        self._recv_buf = bytearray()
        self._expected_remaining: int | None = None

        self._closed = False

        # Register handlers on the reliable DataChannel.
        self._reliable_dc.on("message", self._on_message)
        self._reliable_dc.on("close", self._on_dc_close)
        self._reliable_dc.on("error", lambda e: logger.error("reliable DC error: %s", e))

        # Monitor PeerConnection state.
        if hasattr(pc, 'on'):
            @pc.on("connectionstatechange")
            def _on_conn_state():
                logger.info("PC connectionState: %s", pc.connectionState)

            @pc.on("iceconnectionstatechange")
            def _on_ice_state():
                logger.info("PC iceConnectionState: %s", pc.iceConnectionState)

    def _on_dc_close(self) -> None:
        """Handle reliable DataChannel close."""
        logger.warning("reliable DC closed (readyState=%s)", self._reliable_dc.readyState)
        # Check PC state
        try:
            logger.warning("  PC connectionState=%s iceConnectionState=%s",
                          self._pc.connectionState, self._pc.iceConnectionState)
        except Exception:
            pass

    def _on_message(self, data: bytes) -> None:
        """Handle an incoming DataChannel message (one segment)."""
        logger.info("DC recv: %d bytes, hex=%s", len(data), data[:80].hex())
        if len(data) < 2:
            logger.warning("received segment too short: %d bytes", len(data))
            return

        remaining = data[0]
        payload = data[1:]

        # Validate segment ordering.
        if self._expected_remaining is not None:
            if remaining != self._expected_remaining - 1:
                logger.warning(
                    "segment ordering error: expected remaining=%d, got=%d",
                    self._expected_remaining - 1,
                    remaining,
                )
                self._recv_buf.clear()
                self._expected_remaining = None
                return

        self._expected_remaining = remaining
        self._recv_buf.extend(payload)

        if remaining == 0:
            # Packet fully reassembled.
            packet = bytes(self._recv_buf)
            self._recv_buf.clear()
            self._expected_remaining = None
            try:
                self._packets.put_nowait(packet)
            except asyncio.QueueFull:
                logger.warning("packet queue full, dropping packet")

    async def read_packet(self) -> bytes:
        """Read a fully reassembled packet from the reliable channel."""
        return await self._packets.get()

    async def write_packet(self, data: bytes) -> None:
        """Write a packet to the reliable channel, segmenting if needed."""
        if self._closed:
            raise ConnectionError("connection is closed")

        total_segments = max(1, (len(data) + MAX_MESSAGE_SIZE - 1) // MAX_MESSAGE_SIZE)
        if total_segments > MAX_SEGMENTS:
            raise ValueError(
                f"data too large: {len(data)} bytes requires {total_segments} "
                f"segments (max {MAX_SEGMENTS})"
            )

        remaining = total_segments - 1
        offset = 0
        while offset < len(data):
            end = min(offset + MAX_MESSAGE_SIZE, len(data))
            segment = bytes([remaining]) + data[offset:end]
            logger.info("DC send: %d bytes, hex=%s", len(segment), segment[:80].hex())
            self._reliable_dc.send(segment)
            offset = end
            remaining -= 1

        # For single-byte or empty data edge case.
        if len(data) == 0:
            self._reliable_dc.send(bytes([0]))

    async def close(self) -> None:
        """Close the WebRTC PeerConnection and all data channels."""
        if self._closed:
            return
        self._closed = True
        try:
            if self._reliable_dc:
                self._reliable_dc.close()
            if self._unreliable_dc:
                self._unreliable_dc.close()
            if self._pc:
                await self._pc.close()
        except Exception as e:
            logger.debug("error closing NetherNet connection: %s", e)

    def batch_header(self) -> bytes | None:
        """NetherNet does not use batch headers."""
        return None

    def disable_encryption(self) -> bool:
        """NetherNet uses DTLS for encryption; Minecraft-layer encryption is disabled."""
        return True
