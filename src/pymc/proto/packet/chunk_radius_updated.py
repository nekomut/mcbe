"""ChunkRadiusUpdated packet - server responds with allowed chunk radius."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CHUNK_RADIUS_UPDATED
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ChunkRadiusUpdated(Packet):
    packet_id = ID_CHUNK_RADIUS_UPDATED
    chunk_radius: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.chunk_radius)

    @classmethod
    def read(cls, r: PacketReader) -> ChunkRadiusUpdated:
        return cls(chunk_radius=r.varint32())
