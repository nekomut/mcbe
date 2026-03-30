"""Packet: SubChunkRequest."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SUB_CHUNK_REQUEST
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import SubChunkPos


@register_server_packet
@dataclass
class SubChunkRequest(Packet):
    packet_id = ID_SUB_CHUNK_REQUEST
    dimension: int = 0
    position: SubChunkPos = 0
    offsets: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.dimension)
        w.sub_chunk_pos(self.position)
        w.byte_slice(self.offsets)

    @classmethod
    def read(cls, r: PacketReader) -> SubChunkRequest:
        return cls(
            dimension=r.varint32(),
            position=r.sub_chunk_pos(),
            offsets=r.byte_slice(),
        )
