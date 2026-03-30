"""Packet: Respawn."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_RESPAWN
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class Respawn(Packet):
    packet_id = ID_RESPAWN
    position: Vec3 = 0
    state: int = 0
    entity_runtime_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.vec3(self.position)
        w.uint8(self.state)
        w.varuint64(self.entity_runtime_id)

    @classmethod
    def read(cls, r: PacketReader) -> Respawn:
        return cls(
            position=r.vec3(),
            state=r.uint8(),
            entity_runtime_id=r.varuint64(),
        )
