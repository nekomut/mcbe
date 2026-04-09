"""Binary I/O for Minecraft Bedrock Edition protocol.

Provides PacketReader and PacketWriter for encoding/decoding protocol data
using little-endian byte order, varint encoding, and Minecraft-specific types.
"""

from __future__ import annotations

import struct
from io import BytesIO
from typing import Callable, TypeVar
from uuid import UUID

from mcbe.proto.types import (
    RGBA,
    BlockPos,
    ChunkPos,
    SubChunkPos,
    Vec2,
    Vec3,
)

T = TypeVar("T")


class PacketReader:
    """Reads binary data from a buffer in Minecraft Bedrock protocol format."""

    __slots__ = ("_buf",)

    def __init__(self, data: bytes | bytearray | BytesIO) -> None:
        if isinstance(data, (bytes, bytearray)):
            self._buf = BytesIO(data)
        else:
            self._buf = data

    @property
    def remaining(self) -> int:
        pos = self._buf.tell()
        self._buf.seek(0, 2)
        end = self._buf.tell()
        self._buf.seek(pos)
        return end - pos

    # ── Primitives ──

    def uint8(self) -> int:
        data = self._buf.read(1)
        if len(data) < 1:
            raise EOFError("unexpected end of data reading uint8")
        return data[0]

    def int8(self) -> int:
        return struct.unpack("<b", self._buf.read(1))[0]

    def bool(self) -> bool:
        return self.uint8() != 0

    def uint16(self) -> int:
        return struct.unpack("<H", self._buf.read(2))[0]

    def int16(self) -> int:
        return struct.unpack("<h", self._buf.read(2))[0]

    def uint32(self) -> int:
        return struct.unpack("<I", self._buf.read(4))[0]

    def int32(self) -> int:
        return struct.unpack("<i", self._buf.read(4))[0]

    def be_int32(self) -> int:
        return struct.unpack(">i", self._buf.read(4))[0]

    def uint64(self) -> int:
        return struct.unpack("<Q", self._buf.read(8))[0]

    def int64(self) -> int:
        return struct.unpack("<q", self._buf.read(8))[0]

    def float32(self) -> float:
        return struct.unpack("<f", self._buf.read(4))[0]

    def float64(self) -> float:
        return struct.unpack("<d", self._buf.read(8))[0]

    # ── Varints (LEB128 / zigzag) ──

    def varuint32(self) -> int:
        result = 0
        for i in range(0, 35, 7):
            b = self.uint8()
            result |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                return result & 0xFFFFFFFF
        raise ValueError("varuint32 overflows 5 bytes")

    def varint32(self) -> int:
        ux = self.varuint32()
        x = ux >> 1
        if ux & 1:
            x = ~x
        if x > 0x7FFFFFFF:
            x -= 0x100000000
        return x

    def varuint64(self) -> int:
        result = 0
        for i in range(0, 70, 7):
            b = self.uint8()
            result |= (b & 0x7F) << i
            if (b & 0x80) == 0:
                return result
        raise ValueError("varuint64 overflows 10 bytes")

    def varint64(self) -> int:
        ux = self.varuint64()
        x = ux >> 1
        if ux & 1:
            x = ~x
        return x

    # ── Strings / bytes ──

    def string(self) -> str:
        length = self.varuint32()
        if length > 0x7FFFFFFF:
            raise ValueError("string length overflows a 32-bit integer")
        data = self._buf.read(length)
        if len(data) < length:
            raise EOFError("unexpected end of data reading string")
        return data.decode("utf-8")

    def string_utf(self) -> str:
        length = self.int16()
        if length < 0:
            raise ValueError("negative string length")
        data = self._buf.read(length)
        if len(data) < length:
            raise EOFError("unexpected end of data reading string_utf")
        return data.decode("utf-8")

    def byte_slice(self) -> bytes:
        length = self.varuint32()
        data = self._buf.read(length)
        if len(data) < length:
            raise EOFError("unexpected end of data reading byte_slice")
        return bytes(data)

    def bytes_remaining(self) -> bytes:
        return self._buf.read()

    # ── Minecraft types ──

    def vec3(self) -> Vec3:
        return Vec3(self.float32(), self.float32(), self.float32())

    def vec2(self) -> Vec2:
        return Vec2(self.float32(), self.float32())

    def block_pos(self) -> BlockPos:
        return BlockPos(self.varint32(), self.varint32(), self.varint32())

    def chunk_pos(self) -> ChunkPos:
        return ChunkPos(self.varint32(), self.varint32())

    def sub_chunk_pos(self) -> SubChunkPos:
        return SubChunkPos(self.varint32(), self.varint32(), self.varint32())

    def sound_pos(self) -> Vec3:
        bp = self.block_pos()
        return Vec3(bp.x / 8.0, bp.y / 8.0, bp.z / 8.0)

    def byte_float(self) -> float:
        return self.uint8() * (360.0 / 256.0)

    def uuid(self) -> UUID:
        b = bytearray(self._buf.read(16))
        if len(b) < 16:
            raise EOFError("unexpected end of data reading UUID")
        # Reverse two halves for LE→BE conversion
        b[0:8] = b[0:8][::-1]
        b[8:16] = b[8:16][::-1]
        return UUID(bytes=bytes(b))

    def rgb(self) -> RGBA:
        r = self.float32()
        g = self.float32()
        b = self.float32()
        return RGBA(r=int(r * 255), g=int(g * 255), b=int(b * 255), a=255)

    def rgba(self) -> RGBA:
        v = self.uint32()
        return RGBA.from_uint32(v)

    def argb(self) -> RGBA:
        v = self.int32()
        return RGBA(
            a=v & 0xFF,
            r=(v >> 8) & 0xFF,
            g=(v >> 16) & 0xFF,
            b=(v >> 24) & 0xFF,
        )

    def be_argb(self) -> RGBA:
        v = self.be_int32()
        return RGBA(
            a=v & 0xFF,
            r=(v >> 8) & 0xFF,
            g=(v >> 16) & 0xFF,
            b=(v >> 24) & 0xFF,
        )

    def var_rgba(self) -> RGBA:
        v = self.varuint32()
        return RGBA.from_uint32(v)

    # ── Helpers ──

    def read_slice(self, read_fn: Callable[[], T]) -> list[T]:
        count = self.varuint32()
        return [read_fn() for _ in range(count)]

    def read_slice_uint8(self, read_fn: Callable[[], T]) -> list[T]:
        count = self.uint8()
        return [read_fn() for _ in range(count)]

    def read_slice_uint16(self, read_fn: Callable[[], T]) -> list[T]:
        count = self.uint16()
        return [read_fn() for _ in range(count)]

    def read_slice_uint32(self, read_fn: Callable[[], T]) -> list[T]:
        count = self.uint32()
        return [read_fn() for _ in range(count)]

    def read_optional(self, read_fn: Callable[[], T]) -> T | None:
        if self.bool():
            return read_fn()
        return None

    def nbt(self) -> dict:
        """Read NBT data (NetworkLittleEndian) from the remaining buffer."""
        from mcbe.nbt.codec import decode as nbt_decode
        pos = self._buf.tell()
        remaining = self._buf.read()
        if not remaining:
            return {}
        result = nbt_decode(remaining)
        # We need to figure out how many bytes were consumed.
        # Re-encode to estimate, or use a streaming approach.
        # For simplicity, encode the result back to get the length.
        from mcbe.nbt.codec import encode as nbt_encode
        encoded = nbt_encode(result)
        self._buf.seek(pos + len(encoded))
        return result

    def nbt_typed(self) -> dict[str, tuple[int, object]]:
        """Read NBT data with type preservation (NetworkLittleEndian).

        Returns a typed compound: ``dict[str, (tag_type, value)]``.
        Uses streaming decode so buffer position is advanced correctly.
        """
        from mcbe.chunk import _decode_typed, _TAG_COMPOUND, _TAG_END, _nle_read_string
        tag_type = self._buf.read(1)
        if not tag_type or tag_type[0] == _TAG_END:
            return {}
        _nle_read_string(self._buf)  # root name
        result = _decode_typed(self._buf, _TAG_COMPOUND)
        return result  # type: ignore[return-value]


class PacketWriter:
    """Writes binary data to a buffer in Minecraft Bedrock protocol format."""

    __slots__ = ("_buf",)

    def __init__(self, buf: BytesIO | None = None) -> None:
        self._buf = buf or BytesIO()

    def data(self) -> bytes:
        return self._buf.getvalue()

    # ── Primitives ──

    def uint8(self, v: int) -> None:
        self._buf.write(bytes([v & 0xFF]))

    def int8(self, v: int) -> None:
        self._buf.write(struct.pack("<b", v))

    def bool(self, v: bool) -> None:
        self.uint8(1 if v else 0)

    def uint16(self, v: int) -> None:
        self._buf.write(struct.pack("<H", v))

    def int16(self, v: int) -> None:
        self._buf.write(struct.pack("<h", v))

    def uint32(self, v: int) -> None:
        self._buf.write(struct.pack("<I", v & 0xFFFFFFFF))

    def int32(self, v: int) -> None:
        self._buf.write(struct.pack("<i", v))

    def be_int32(self, v: int) -> None:
        self._buf.write(struct.pack(">i", v))

    def uint64(self, v: int) -> None:
        self._buf.write(struct.pack("<Q", v))

    def int64(self, v: int) -> None:
        self._buf.write(struct.pack("<q", v))

    def float32(self, v: float) -> None:
        self._buf.write(struct.pack("<f", v))

    def float64(self, v: float) -> None:
        self._buf.write(struct.pack("<d", v))

    # ── Varints ──

    def varuint32(self, v: int) -> None:
        v &= 0xFFFFFFFF
        while True:
            b = v & 0x7F
            v >>= 7
            if v != 0:
                b |= 0x80
            self._buf.write(bytes([b]))
            if v == 0:
                break

    def varint32(self, v: int) -> None:
        # Zigzag encode
        self.varuint32((v << 1) ^ (v >> 31))

    def varuint64(self, v: int) -> None:
        v &= 0xFFFFFFFFFFFFFFFF
        while True:
            b = v & 0x7F
            v >>= 7
            if v != 0:
                b |= 0x80
            self._buf.write(bytes([b]))
            if v == 0:
                break

    def varint64(self, v: int) -> None:
        self.varuint64((v << 1) ^ (v >> 63))

    # ── Strings / bytes ──

    def string(self, v: str) -> None:
        encoded = v.encode("utf-8")
        self.varuint32(len(encoded))
        self._buf.write(encoded)

    def string_utf(self, v: str) -> None:
        encoded = v.encode("utf-8")
        self.int16(len(encoded))
        self._buf.write(encoded)

    def byte_slice(self, v: bytes) -> None:
        self.varuint32(len(v))
        self._buf.write(v)

    def bytes_raw(self, v: bytes) -> None:
        self._buf.write(v)

    # ── Minecraft types ──

    def vec3(self, v: Vec3) -> None:
        self.float32(v.x)
        self.float32(v.y)
        self.float32(v.z)

    def vec2(self, v: Vec2) -> None:
        self.float32(v.x)
        self.float32(v.y)

    def block_pos(self, v: BlockPos) -> None:
        self.varint32(v.x)
        self.varint32(v.y)
        self.varint32(v.z)

    def chunk_pos(self, v: ChunkPos) -> None:
        self.varint32(v.x)
        self.varint32(v.z)

    def sub_chunk_pos(self, v: SubChunkPos) -> None:
        self.varint32(v.x)
        self.varint32(v.y)
        self.varint32(v.z)

    def sound_pos(self, v: Vec3) -> None:
        self.block_pos(BlockPos(int(v.x * 8), int(v.y * 8), int(v.z * 8)))

    def byte_float(self, v: float) -> None:
        self.uint8(int(v / (360.0 / 256.0)) & 0xFF)

    def uuid(self, v: UUID) -> None:
        b = bytearray(v.bytes)
        # Reverse two halves for BE→LE conversion
        b[0:8] = b[0:8][::-1]
        b[8:16] = b[8:16][::-1]
        self._buf.write(b)

    def rgb(self, v: RGBA) -> None:
        self.float32(v.r / 255.0)
        self.float32(v.g / 255.0)
        self.float32(v.b / 255.0)

    def rgba(self, v: RGBA) -> None:
        self.uint32(v.to_uint32())

    def argb(self, v: RGBA) -> None:
        val = v.a | (v.r << 8) | (v.g << 16) | (v.b << 24)
        self.int32(val if val < 0x80000000 else val - 0x100000000)

    def be_argb(self, v: RGBA) -> None:
        val = v.a | (v.r << 8) | (v.g << 16) | (v.b << 24)
        self.be_int32(val if val < 0x80000000 else val - 0x100000000)

    def var_rgba(self, v: RGBA) -> None:
        self.varuint32(v.to_uint32())

    # ── Helpers ──

    def write_slice(self, items: list, write_fn: Callable[[...], None]) -> None:
        self.varuint32(len(items))
        for item in items:
            write_fn(item)

    def write_slice_uint8(self, items: list, write_fn: Callable) -> None:
        self.uint8(len(items))
        for item in items:
            write_fn(item)

    def write_slice_uint16(self, items: list, write_fn: Callable) -> None:
        self.uint16(len(items))
        for item in items:
            write_fn(item)

    def write_slice_uint32(self, items: list, write_fn: Callable) -> None:
        self.uint32(len(items))
        for item in items:
            write_fn(item)

    def write_optional(self, value: T | None, write_fn: Callable[[T], None]) -> None:
        if value is not None:
            self.bool(True)
            write_fn(value)
        else:
            self.bool(False)

    def nbt(self, value: dict) -> None:
        """Write NBT data (NetworkLittleEndian)."""
        from mcbe.nbt.codec import encode as nbt_encode
        self._buf.write(nbt_encode(value))
