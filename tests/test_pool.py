"""Tests for packet pool, batch encoding/decoding."""

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.pool import (
    COMPRESSION_FLATE,
    Packet,
    UnknownPacket,
    decode_batch,
    decode_packet,
    encode_batch,
    encode_packet,
    register_server_packet,
    server_pool,
)


@dataclass
class _TestPacket(Packet):
    packet_id = 0xFE
    value: int = 0
    name: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.value)
        w.string(self.name)

    @classmethod
    def read(cls, r: PacketReader) -> "_TestPacket":
        return cls(value=r.varuint32(), name=r.string())


register_server_packet(_TestPacket)


class TestEncodeDecodePacket:
    def test_roundtrip(self):
        pk = _TestPacket(value=42, name="hello")
        data = encode_packet(pk)
        pool = server_pool()
        result = decode_packet(data, pool)
        assert isinstance(result, _TestPacket)
        assert result.value == 42
        assert result.name == "hello"

    def test_unknown_packet(self):
        w = PacketWriter()
        w.varuint32(0x3FF)  # Max 10-bit ID, unlikely registered
        w.bytes_raw(b"\x01\x02\x03")
        data = w.data()
        result = decode_packet(data, {})
        assert isinstance(result, UnknownPacket)
        assert result.packet_id == 0x3FF


class TestBatchEncoding:
    def test_no_compression(self):
        pk = _TestPacket(value=1, name="a")
        pkt_bytes = encode_packet(pk)
        batch = encode_batch([pkt_bytes])
        packets = decode_batch(batch)
        assert len(packets) == 1
        pool = server_pool()
        result = decode_packet(packets[0], pool)
        assert isinstance(result, _TestPacket)
        assert result.value == 1

    def test_multiple_packets(self):
        pkts = [encode_packet(_TestPacket(value=i, name=f"p{i}")) for i in range(5)]
        batch = encode_batch(pkts)
        packets = decode_batch(batch)
        assert len(packets) == 5

    def test_flate_compression(self):
        pk = _TestPacket(value=99, name="compressed")
        pkt_bytes = encode_packet(pk)
        batch = encode_batch(
            [pkt_bytes], compression=COMPRESSION_FLATE, compression_threshold=0
        )
        packets = decode_batch(batch, compression=COMPRESSION_FLATE)
        assert len(packets) == 1
        pool = server_pool()
        result = decode_packet(packets[0], pool)
        assert isinstance(result, _TestPacket)
        assert result.value == 99
        assert result.name == "compressed"

    def test_below_threshold_no_compress(self):
        pk = _TestPacket(value=1, name="x")
        pkt_bytes = encode_packet(pk)
        batch = encode_batch(
            [pkt_bytes], compression=COMPRESSION_FLATE, compression_threshold=99999
        )
        packets = decode_batch(batch, compression=COMPRESSION_FLATE)
        assert len(packets) == 1

    def test_empty_batch(self):
        batch = encode_batch([])
        packets = decode_batch(batch)
        assert packets == []
