"""Packet base class, pool registry, and batch encoder/decoder.

The Packet base class defines the interface all packets must implement.
PacketPool maps packet IDs to factory functions for decoding.
BatchEncoder/BatchDecoder handle compression and encryption of packet batches.
"""

from __future__ import annotations

import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import Callable, Type

from pymc.proto.io import PacketReader, PacketWriter

# Batch header byte (0xfe) used to identify Minecraft packet batches.
BATCH_HEADER = 0xFE

# Maximum packets in a single batch.
MAX_BATCH_SIZE = 812

# Compression algorithm IDs.
COMPRESSION_NONE = 0xFF
COMPRESSION_FLATE = 0x00
COMPRESSION_SNAPPY = 0x01


class Packet(ABC):
    """Base class for all Minecraft Bedrock Edition packets."""

    packet_id: int = 0

    @abstractmethod
    def write(self, w: PacketWriter) -> None:
        """Serialize this packet's fields to the writer."""
        ...

    @classmethod
    @abstractmethod
    def read(cls, r: PacketReader) -> Packet:
        """Deserialize a packet from the reader."""
        ...


@dataclass
class UnknownPacket(Packet):
    """Represents a packet with an unrecognized ID."""
    packet_id: int = 0
    payload: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.bytes_raw(self.payload)

    @classmethod
    def read(cls, r: PacketReader) -> UnknownPacket:
        return cls(payload=r.bytes_remaining())


# Type alias for packet factory functions.
PacketFactory = Callable[[], Type[Packet]]

# Packet pool: maps packet ID → packet class.
PacketPool = dict[int, Type[Packet]]

# Global registries.
_server_packets: PacketPool = {}
_client_packets: PacketPool = {}


def register_server_packet(packet_cls: Type[Packet]) -> Type[Packet]:
    """Register a packet class as server-originating."""
    _server_packets[packet_cls.packet_id] = packet_cls
    return packet_cls


def register_client_packet(packet_cls: Type[Packet]) -> Type[Packet]:
    """Register a packet class as client-originating."""
    _client_packets[packet_cls.packet_id] = packet_cls
    return packet_cls


def register_bidirectional(packet_cls: Type[Packet]) -> Type[Packet]:
    """Register a packet class as both server and client-originating."""
    register_server_packet(packet_cls)
    register_client_packet(packet_cls)
    return packet_cls


def server_pool() -> PacketPool:
    """Return a copy of the server packet pool."""
    return dict(_server_packets)


def client_pool() -> PacketPool:
    """Return a copy of the client packet pool."""
    return dict(_client_packets)


def encode_packet(pk: Packet) -> bytes:
    """Encode a single packet to bytes (header + payload)."""
    w = PacketWriter()
    # Packet header: varuint32 of (packet_id << 0) | (sender_subclient << 10) | (target_subclient << 12)
    # For now, we only use the packet ID (no sub-clients).
    w.varuint32(pk.packet_id)
    pk.write(w)
    return w.data()


def decode_packet(data: bytes, pool: PacketPool) -> Packet:
    """Decode a single packet from bytes using the given pool."""
    r = PacketReader(data)
    header = r.varuint32()
    packet_id = header & 0x3FF

    packet_cls = pool.get(packet_id)
    if packet_cls is None:
        pk = UnknownPacket.read(r)
        pk.packet_id = packet_id
        return pk
    return packet_cls.read(r)


def encode_batch(
    packets: list[bytes],
    compression: int | None = None,
    compression_threshold: int = 256,
) -> bytes:
    """Encode a batch of pre-encoded packets into a single batch payload.

    Args:
        packets: List of already-encoded packet bytes.
        compression: Compression algorithm ID. None = no compression.
        compression_threshold: Minimum size to apply compression.

    Returns:
        The batch payload (header + optional compression ID + data).
    """
    buf = BytesIO()
    for pkt in packets:
        # Each packet prefixed with varuint32 length.
        _write_varuint32(buf, len(pkt))
        buf.write(pkt)

    data = buf.getvalue()
    result = bytearray([BATCH_HEADER])

    if compression is not None:
        if len(data) < compression_threshold:
            # Below threshold: no compression, but mark as uncompressed.
            result.append(COMPRESSION_NONE)
        elif compression == COMPRESSION_FLATE:
            data = zlib.compress(data)
            result.append(COMPRESSION_FLATE)
        elif compression == COMPRESSION_SNAPPY:
            try:
                import snappy
                data = snappy.compress(data)
            except ImportError:
                raise RuntimeError("python-snappy required for snappy compression")
            result.append(COMPRESSION_SNAPPY)
        else:
            result.append(compression & 0xFF)

    result.extend(data)
    return bytes(result)


def decode_batch(
    data: bytes,
    compression: int | None = None,
    max_decompressed: int = 16 * 1024 * 1024,
) -> list[bytes]:
    """Decode a batch payload into individual packet byte arrays.

    Args:
        data: Raw batch payload.
        compression: Expected compression algorithm. None = no compression.
        max_decompressed: Maximum decompressed size.

    Returns:
        List of raw packet bytes (each still needs decode_packet).
    """
    if len(data) == 0:
        return []
    if data[0] != BATCH_HEADER:
        raise ValueError(f"invalid batch header: 0x{data[0]:02x}, expected 0xfe")
    data = data[1:]

    if compression is not None:
        comp_id = data[0]
        data = data[1:]
        if comp_id == COMPRESSION_NONE:
            pass  # No compression
        elif comp_id == COMPRESSION_FLATE:
            data = zlib.decompress(data, bufsize=max_decompressed)
        elif comp_id == COMPRESSION_SNAPPY:
            try:
                import snappy
                data = snappy.decompress(data)
            except ImportError:
                raise RuntimeError("python-snappy required for snappy decompression")
        else:
            raise ValueError(f"unknown compression algorithm: {comp_id}")

    # Parse individual packets.
    packets: list[bytes] = []
    buf = BytesIO(data)
    while buf.tell() < len(data):
        length = _read_varuint32(buf)
        pkt = buf.read(length)
        if len(pkt) < length:
            raise EOFError("incomplete packet in batch")
        packets.append(pkt)

    if len(packets) > MAX_BATCH_SIZE:
        raise ValueError(f"batch contains {len(packets)} packets, max is {MAX_BATCH_SIZE}")

    return packets


def _write_varuint32(buf: BytesIO, v: int) -> None:
    v &= 0xFFFFFFFF
    while v >= 0x80:
        buf.write(bytes([(v & 0x7F) | 0x80]))
        v >>= 7
    buf.write(bytes([v]))


def _read_varuint32(buf: BytesIO) -> int:
    result = 0
    for i in range(0, 35, 7):
        b = buf.read(1)
        if len(b) == 0:
            raise EOFError("unexpected end of data reading varuint32")
        b = b[0]
        result |= (b & 0x7F) << i
        if (b & 0x80) == 0:
            return result
    raise ValueError("varuint32 overflows")
