"""Packet: MoveActorAbsolute."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOVE_ACTOR_ABSOLUTE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class MoveActorAbsolute(Packet):
    packet_id = ID_MOVE_ACTOR_ABSOLUTE
    entity_runtime_id: int = 0
    flags: int = 0
    position: Vec3 = 0
    rotation: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.uint8(self.flags)
        w.vec3(self.position)
        w.vec3(self.rotation)

    @classmethod
    def read(cls, r: PacketReader) -> MoveActorAbsolute:
        return cls(
            entity_runtime_id=r.varuint64(),
            flags=r.uint8(),
            position=r.vec3(),
            rotation=r.vec3(),
        )
