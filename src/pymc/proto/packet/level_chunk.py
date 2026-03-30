"""Packet: LevelChunk."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LEVEL_CHUNK
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import ChunkPos

# SubChunkCount special values
SUB_CHUNK_REQUEST_MODE_LIMITED = 0xFFFFFFFF - 1  # protocol.SubChunkRequestModeLimited
SUB_CHUNK_REQUEST_MODE_LIMITLESS = 0xFFFFFFFF  # protocol.SubChunkRequestModeLimitless


@register_server_packet
@dataclass
class LevelChunk(Packet):
    packet_id = ID_LEVEL_CHUNK
    position: ChunkPos = field(default_factory=ChunkPos)
    dimension: int = 0
    sub_chunk_count: int = 0
    highest_sub_chunk: int = 0
    cache_enabled: bool = False
    blob_hashes: list[int] = field(default_factory=list)
    raw_payload: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.chunk_pos(self.position)
        w.varint32(self.dimension)
        w.varuint32(self.sub_chunk_count)
        if self.sub_chunk_count == SUB_CHUNK_REQUEST_MODE_LIMITED:
            w.uint16(self.highest_sub_chunk)
        w.bool(self.cache_enabled)
        if self.cache_enabled:
            w.varuint32(len(self.blob_hashes))
            for h in self.blob_hashes:
                w.uint64(h)
        w.byte_slice(self.raw_payload)

    @classmethod
    def read(cls, r: PacketReader) -> LevelChunk:
        position = r.chunk_pos()
        dimension = r.varint32()
        sub_chunk_count = r.varuint32()
        highest_sub_chunk = 0
        if sub_chunk_count == SUB_CHUNK_REQUEST_MODE_LIMITED:
            highest_sub_chunk = r.uint16()
        cache_enabled = r.bool()
        blob_hashes: list[int] = []
        if cache_enabled:
            count = r.varuint32()
            blob_hashes = [r.uint64() for _ in range(count)]
        raw_payload = r.byte_slice()
        return cls(
            position=position,
            dimension=dimension,
            sub_chunk_count=sub_chunk_count,
            highest_sub_chunk=highest_sub_chunk,
            cache_enabled=cache_enabled,
            blob_hashes=blob_hashes,
            raw_payload=raw_payload,
        )
