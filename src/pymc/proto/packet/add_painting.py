"""Packet: AddPainting."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADD_PAINTING
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class AddPainting(Packet):
    packet_id = ID_ADD_PAINTING
    entity_unique_id: int = 0
    entity_runtime_id: int = 0
    position: Vec3 = 0
    direction: int = 0
    title: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)
        w.varuint64(self.entity_runtime_id)
        w.vec3(self.position)
        w.varint32(self.direction)
        w.string(self.title)

    @classmethod
    def read(cls, r: PacketReader) -> AddPainting:
        return cls(
            entity_unique_id=r.varint64(),
            entity_runtime_id=r.varuint64(),
            position=r.vec3(),
            direction=r.varint32(),
            title=r.string(),
        )
