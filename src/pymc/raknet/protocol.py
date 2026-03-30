"""RakNet protocol constants and packet definitions.

Based on RakNet specification used by Minecraft Bedrock Edition.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

# ── RakNet Magic ────────────────────────────────────────────────

RAKNET_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")

# ── Packet IDs ──────────────────────────────────────────────────

UNCONNECTED_PING = 0x01
UNCONNECTED_PING_OPEN = 0x02
UNCONNECTED_PONG = 0x1C
OPEN_CONNECTION_REQUEST_1 = 0x05
OPEN_CONNECTION_REPLY_1 = 0x06
OPEN_CONNECTION_REQUEST_2 = 0x07
OPEN_CONNECTION_REPLY_2 = 0x08
CONNECTION_REQUEST = 0x09
CONNECTION_REQUEST_ACCEPTED = 0x10
NEW_INCOMING_CONNECTION = 0x13
DISCONNECTION_NOTIFICATION = 0x15
CONNECTED_PING = 0x00
CONNECTED_PONG = 0x03

# Frame set range: 0x80-0x8f
FRAME_SET_MIN = 0x80
FRAME_SET_MAX = 0x8F

ACK = 0xC0
NACK = 0xA0

GAME_PACKET = 0xFE

# ── RakNet Protocol Version ────────────────────────────────────

RAKNET_PROTOCOL_VERSION = 11

# ── Reliability Types ───────────────────────────────────────────

UNRELIABLE = 0
UNRELIABLE_SEQUENCED = 1
RELIABLE = 2
RELIABLE_ORDERED = 3
RELIABLE_SEQUENCED = 4
UNRELIABLE_WITH_ACK = 5
RELIABLE_WITH_ACK = 6
RELIABLE_ORDERED_WITH_ACK = 7

RELIABLE_TYPES = {RELIABLE, RELIABLE_ORDERED, RELIABLE_SEQUENCED,
                  RELIABLE_WITH_ACK, RELIABLE_ORDERED_WITH_ACK}
ORDERED_TYPES = {UNRELIABLE_SEQUENCED, RELIABLE_ORDERED, RELIABLE_SEQUENCED,
                 RELIABLE_ORDERED_WITH_ACK}
SEQUENCED_TYPES = {UNRELIABLE_SEQUENCED, RELIABLE_SEQUENCED}

# ── Default MTU ─────────────────────────────────────────────────

DEFAULT_MTU = 1400
MIN_MTU = 400
MAX_MTU = 1492

# ── Binary helpers ──────────────────────────────────────────────


def write_uint24le(value: int) -> bytes:
    """Write a 24-bit unsigned integer in little-endian."""
    return struct.pack("<I", value)[:3]


def read_uint24le(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Read a 24-bit unsigned integer in little-endian. Returns (value, new_offset)."""
    return struct.unpack("<I", data[offset:offset + 3] + b"\x00")[0], offset + 3


def write_address(host: str, port: int) -> bytes:
    """Write a RakNet address (IPv4 only)."""
    parts = host.split(".")
    buf = b"\x04"  # IPv4
    for p in parts:
        buf += struct.pack("B", ~int(p) & 0xFF)
    buf += struct.pack(">H", port)
    return buf


def read_address(data: bytes, offset: int = 0) -> tuple[str, int, int]:
    """Read a RakNet address. Returns (host, port, new_offset)."""
    version = data[offset]
    offset += 1
    if version == 4:
        parts = [str(~data[offset + i] & 0xFF) for i in range(4)]
        offset += 4
        port = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        return ".".join(parts), port, offset
    elif version == 6:
        # IPv6: skip family(2) + port(2) + flow(4) + addr(16) + scope(4)
        offset += 2
        port = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        offset += 4  # flow info
        addr_bytes = data[offset:offset + 16]
        offset += 16
        offset += 4  # scope id
        host = ":".join(f"{addr_bytes[i]:02x}{addr_bytes[i+1]:02x}" for i in range(0, 16, 2))
        return host, port, offset
    else:
        raise ValueError(f"Unknown address version: {version}")


# ── Frame ───────────────────────────────────────────────────────


@dataclass
class Frame:
    """A single RakNet frame within a frame set."""

    reliability: int = RELIABLE_ORDERED
    body: bytes = b""
    reliable_index: int = 0
    sequenced_index: int = 0
    ordered_index: int = 0
    order_channel: int = 0
    # Fragmentation
    fragmented: bool = False
    compound_size: int = 0
    compound_id: int = 0
    fragment_index: int = 0

    def encode(self) -> bytes:
        """Encode this frame to bytes."""
        flags = (self.reliability << 5)
        if self.fragmented:
            flags |= 0x10
        buf = struct.pack("B", flags)
        # Length in bits
        buf += struct.pack(">H", len(self.body) * 8)

        if self.reliability in RELIABLE_TYPES:
            buf += write_uint24le(self.reliable_index)
        if self.reliability in SEQUENCED_TYPES:
            buf += write_uint24le(self.sequenced_index)
        if self.reliability in ORDERED_TYPES:
            buf += write_uint24le(self.ordered_index)
            buf += struct.pack("B", self.order_channel)

        if self.fragmented:
            buf += struct.pack(">I", self.compound_size)
            buf += struct.pack(">H", self.compound_id)
            buf += struct.pack(">I", self.fragment_index)

        buf += self.body
        return buf

    @classmethod
    def decode(cls, data: bytes, offset: int = 0) -> tuple[Frame, int]:
        """Decode a frame from bytes. Returns (frame, new_offset)."""
        flags = data[offset]
        offset += 1
        reliability = (flags >> 5) & 0x07
        fragmented = bool(flags & 0x10)

        length_bits = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        length_bytes = (length_bits + 7) // 8

        reliable_index = 0
        sequenced_index = 0
        ordered_index = 0
        order_channel = 0

        if reliability in RELIABLE_TYPES:
            reliable_index, offset = read_uint24le(data, offset)
        if reliability in SEQUENCED_TYPES:
            sequenced_index, offset = read_uint24le(data, offset)
        if reliability in ORDERED_TYPES:
            ordered_index, offset = read_uint24le(data, offset)
            order_channel = data[offset]
            offset += 1

        compound_size = 0
        compound_id = 0
        fragment_index = 0
        if fragmented:
            compound_size = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4
            compound_id = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            fragment_index = struct.unpack(">I", data[offset:offset + 4])[0]
            offset += 4

        body = data[offset:offset + length_bytes]
        offset += length_bytes

        return cls(
            reliability=reliability,
            body=body,
            reliable_index=reliable_index,
            sequenced_index=sequenced_index,
            ordered_index=ordered_index,
            order_channel=order_channel,
            fragmented=fragmented,
            compound_size=compound_size,
            compound_id=compound_id,
            fragment_index=fragment_index,
        ), offset


# ── Frame Set ───────────────────────────────────────────────────


def encode_frame_set(sequence_number: int, frames: list[Frame]) -> bytes:
    """Encode a frame set packet."""
    buf = struct.pack("B", FRAME_SET_MIN)
    buf += write_uint24le(sequence_number)
    for frame in frames:
        buf += frame.encode()
    return buf


def decode_frame_set(data: bytes) -> tuple[int, list[Frame]]:
    """Decode a frame set packet. Returns (sequence_number, frames)."""
    offset = 1  # skip packet ID
    seq_num, offset = read_uint24le(data, offset)
    frames: list[Frame] = []
    while offset < len(data):
        frame, offset = Frame.decode(data, offset)
        frames.append(frame)
    return seq_num, frames


# ── ACK / NACK ──────────────────────────────────────────────────


def encode_ack(sequence_numbers: list[int]) -> bytes:
    """Encode an ACK packet with the given sequence numbers."""
    return _encode_ack_nack(ACK, sequence_numbers)


def encode_nack(sequence_numbers: list[int]) -> bytes:
    """Encode a NACK packet with the given sequence numbers."""
    return _encode_ack_nack(NACK, sequence_numbers)


def _encode_ack_nack(packet_id: int, numbers: list[int]) -> bytes:
    """Encode ACK/NACK with range compression."""
    if not numbers:
        return struct.pack("B", packet_id) + struct.pack(">H", 0)

    numbers = sorted(set(numbers))
    ranges: list[tuple[int, int]] = []
    start = numbers[0]
    end = start

    for n in numbers[1:]:
        if n == end + 1:
            end = n
        else:
            ranges.append((start, end))
            start = n
            end = n
    ranges.append((start, end))

    buf = struct.pack("B", packet_id)
    buf += struct.pack(">H", len(ranges))
    for start, end in ranges:
        if start == end:
            buf += b"\x01"  # single
            buf += write_uint24le(start)
        else:
            buf += b"\x00"  # range
            buf += write_uint24le(start)
            buf += write_uint24le(end)
    return buf


def decode_ack_nack(data: bytes) -> list[int]:
    """Decode ACK/NACK packet and return sequence numbers."""
    offset = 1  # skip packet ID
    range_count = struct.unpack(">H", data[offset:offset + 2])[0]
    offset += 2

    numbers: list[int] = []
    for _ in range(range_count):
        is_single = data[offset] == 1
        offset += 1
        if is_single:
            n, offset = read_uint24le(data, offset)
            numbers.append(n)
        else:
            start, offset = read_uint24le(data, offset)
            end, offset = read_uint24le(data, offset)
            numbers.extend(range(start, end + 1))
    return numbers
