"""RequestChunkRadius packet - client requests chunk view radius."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REQUEST_CHUNK_RADIUS
from pymc.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class RequestChunkRadius(Packet):
    packet_id = ID_REQUEST_CHUNK_RADIUS
    chunk_radius: int = 0
    max_chunk_radius: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.chunk_radius)
        w.uint8(self.max_chunk_radius)

    @classmethod
    def read(cls, r: PacketReader) -> RequestChunkRadius:
        return cls(
            chunk_radius=r.varint32(),
            max_chunk_radius=r.uint8(),
        )
