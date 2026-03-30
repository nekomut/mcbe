"""Packet: SubChunk.

SubChunkEntry structures are kept as raw bytes because the full type
has not been ported yet. The conditional logic for cache_enabled is noted:
different entry format is used when caching is enabled vs disabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SUB_CHUNK
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import SubChunkPos


@register_server_packet
@dataclass
class SubChunk(Packet):
    packet_id = ID_SUB_CHUNK
    cache_enabled: bool = False
    dimension: int = 0
    position: SubChunkPos = field(default_factory=SubChunkPos)
    sub_chunk_entries: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.bool(self.cache_enabled)
        w.varint32(self.dimension)
        w.sub_chunk_pos(self.position)
        w.bytes_raw(self.sub_chunk_entries)

    @classmethod
    def read(cls, r: PacketReader) -> SubChunk:
        cache_enabled = r.bool()
        dimension = r.varint32()
        position = r.sub_chunk_pos()
        sub_chunk_entries = r.bytes_remaining()
        return cls(
            cache_enabled=cache_enabled,
            dimension=dimension,
            position=position,
            sub_chunk_entries=sub_chunk_entries,
        )
