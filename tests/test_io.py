"""Tests for PacketReader and PacketWriter round-trip correctness."""

import math
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.types import RGBA, BlockPos, ChunkPos, SubChunkPos, Vec2, Vec3


def _roundtrip_primitive(write_method: str, read_method: str, value):
    w = PacketWriter()
    getattr(w, write_method)(value)
    r = PacketReader(w.data())
    result = getattr(r, read_method)()
    return result


class TestPrimitives:
    def test_uint8(self):
        assert _roundtrip_primitive("uint8", "uint8", 0) == 0
        assert _roundtrip_primitive("uint8", "uint8", 255) == 255

    def test_int8(self):
        assert _roundtrip_primitive("int8", "int8", -128) == -128
        assert _roundtrip_primitive("int8", "int8", 127) == 127

    def test_bool(self):
        assert _roundtrip_primitive("bool", "bool", True) is True
        assert _roundtrip_primitive("bool", "bool", False) is False

    def test_uint16(self):
        assert _roundtrip_primitive("uint16", "uint16", 0) == 0
        assert _roundtrip_primitive("uint16", "uint16", 65535) == 65535

    def test_int16(self):
        assert _roundtrip_primitive("int16", "int16", -32768) == -32768
        assert _roundtrip_primitive("int16", "int16", 32767) == 32767

    def test_uint32(self):
        assert _roundtrip_primitive("uint32", "uint32", 0) == 0
        assert _roundtrip_primitive("uint32", "uint32", 0xFFFFFFFF) == 0xFFFFFFFF

    def test_int32(self):
        assert _roundtrip_primitive("int32", "int32", -2147483648) == -2147483648
        assert _roundtrip_primitive("int32", "int32", 2147483647) == 2147483647

    def test_be_int32(self):
        assert _roundtrip_primitive("be_int32", "be_int32", 12345678) == 12345678

    def test_uint64(self):
        assert _roundtrip_primitive("uint64", "uint64", 0) == 0
        assert _roundtrip_primitive("uint64", "uint64", 2**64 - 1) == 2**64 - 1

    def test_int64(self):
        assert _roundtrip_primitive("int64", "int64", -(2**63)) == -(2**63)
        assert _roundtrip_primitive("int64", "int64", 2**63 - 1) == 2**63 - 1

    def test_float32(self):
        result = _roundtrip_primitive("float32", "float32", 3.14)
        assert abs(result - 3.14) < 1e-6

    def test_float64(self):
        result = _roundtrip_primitive("float64", "float64", 3.141592653589793)
        assert result == 3.141592653589793


class TestVarints:
    def test_varuint32_zero(self):
        assert _roundtrip_primitive("varuint32", "varuint32", 0) == 0

    def test_varuint32_small(self):
        assert _roundtrip_primitive("varuint32", "varuint32", 127) == 127

    def test_varuint32_medium(self):
        assert _roundtrip_primitive("varuint32", "varuint32", 300) == 300

    def test_varuint32_large(self):
        assert _roundtrip_primitive("varuint32", "varuint32", 0xFFFFFFFF) == 0xFFFFFFFF

    def test_varint32_positive(self):
        assert _roundtrip_primitive("varint32", "varint32", 150) == 150

    def test_varint32_negative(self):
        assert _roundtrip_primitive("varint32", "varint32", -150) == -150

    def test_varint32_zero(self):
        assert _roundtrip_primitive("varint32", "varint32", 0) == 0

    def test_varint32_min(self):
        assert _roundtrip_primitive("varint32", "varint32", -2147483648) == -2147483648

    def test_varint32_max(self):
        assert _roundtrip_primitive("varint32", "varint32", 2147483647) == 2147483647

    def test_varuint64(self):
        assert _roundtrip_primitive("varuint64", "varuint64", 0) == 0
        assert _roundtrip_primitive("varuint64", "varuint64", 2**64 - 1) == 2**64 - 1

    def test_varint64(self):
        assert _roundtrip_primitive("varint64", "varint64", -1) == -1
        assert _roundtrip_primitive("varint64", "varint64", 123456789) == 123456789


class TestStringsBytes:
    def test_string(self):
        assert _roundtrip_primitive("string", "string", "") == ""
        assert _roundtrip_primitive("string", "string", "hello") == "hello"
        assert _roundtrip_primitive("string", "string", "日本語") == "日本語"

    def test_string_utf(self):
        assert _roundtrip_primitive("string_utf", "string_utf", "test") == "test"

    def test_byte_slice(self):
        assert _roundtrip_primitive("byte_slice", "byte_slice", b"") == b""
        assert _roundtrip_primitive("byte_slice", "byte_slice", b"\x00\x01\x02") == b"\x00\x01\x02"


class TestMinecraftTypes:
    def test_vec3(self):
        w = PacketWriter()
        w.vec3(Vec3(1.0, 2.0, 3.0))
        r = PacketReader(w.data())
        v = r.vec3()
        assert abs(v.x - 1.0) < 1e-6
        assert abs(v.y - 2.0) < 1e-6
        assert abs(v.z - 3.0) < 1e-6

    def test_vec2(self):
        w = PacketWriter()
        w.vec2(Vec2(1.5, 2.5))
        r = PacketReader(w.data())
        v = r.vec2()
        assert abs(v.x - 1.5) < 1e-6
        assert abs(v.y - 2.5) < 1e-6

    def test_block_pos(self):
        w = PacketWriter()
        w.block_pos(BlockPos(10, -20, 30))
        r = PacketReader(w.data())
        bp = r.block_pos()
        assert bp == BlockPos(10, -20, 30)

    def test_chunk_pos(self):
        w = PacketWriter()
        w.chunk_pos(ChunkPos(5, -3))
        r = PacketReader(w.data())
        cp = r.chunk_pos()
        assert cp == ChunkPos(5, -3)

    def test_sub_chunk_pos(self):
        w = PacketWriter()
        w.sub_chunk_pos(SubChunkPos(1, 2, 3))
        r = PacketReader(w.data())
        scp = r.sub_chunk_pos()
        assert scp == SubChunkPos(1, 2, 3)

    def test_byte_float(self):
        w = PacketWriter()
        w.byte_float(180.0)
        r = PacketReader(w.data())
        result = r.byte_float()
        assert abs(result - 180.0) < 2.0  # 1.4 degree precision

    def test_uuid(self):
        original = UUID("12345678-1234-5678-1234-567812345678")
        w = PacketWriter()
        w.uuid(original)
        r = PacketReader(w.data())
        result = r.uuid()
        assert result == original

    def test_rgba(self):
        original = RGBA(r=100, g=150, b=200, a=255)
        w = PacketWriter()
        w.rgba(original)
        r = PacketReader(w.data())
        result = r.rgba()
        assert result.r == 100
        assert result.g == 150
        assert result.b == 200
        assert result.a == 255

    def test_var_rgba(self):
        original = RGBA(r=50, g=100, b=150, a=200)
        w = PacketWriter()
        w.var_rgba(original)
        r = PacketReader(w.data())
        result = r.var_rgba()
        assert result.r == 50
        assert result.g == 100
        assert result.b == 150
        assert result.a == 200


class TestSliceHelpers:
    def test_read_write_slice(self):
        w = PacketWriter()
        w.write_slice(["hello", "world"], w.string)
        r = PacketReader(w.data())
        result = r.read_slice(r.string)
        assert result == ["hello", "world"]

    def test_read_write_slice_empty(self):
        w = PacketWriter()
        w.write_slice([], w.string)
        r = PacketReader(w.data())
        result = r.read_slice(r.string)
        assert result == []

    def test_optional_some(self):
        w = PacketWriter()
        w.write_optional("hello", w.string)
        r = PacketReader(w.data())
        result = r.read_optional(r.string)
        assert result == "hello"

    def test_optional_none(self):
        w = PacketWriter()
        w.write_optional(None, w.string)
        r = PacketReader(w.data())
        result = r.read_optional(r.string)
        assert result is None


class TestMultipleWrites:
    def test_mixed_types(self):
        w = PacketWriter()
        w.varuint32(42)
        w.string("test")
        w.bool(True)
        w.float32(1.5)
        w.block_pos(BlockPos(1, 2, 3))

        r = PacketReader(w.data())
        assert r.varuint32() == 42
        assert r.string() == "test"
        assert r.bool() is True
        assert abs(r.float32() - 1.5) < 1e-6
        assert r.block_pos() == BlockPos(1, 2, 3)
        assert r.remaining == 0
