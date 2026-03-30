"""Packet: SetActorMotion."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_ACTOR_MOTION
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class SetActorMotion(Packet):
    packet_id = ID_SET_ACTOR_MOTION
    entity_runtime_id: int = 0
    velocity: Vec3 = 0
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.vec3(self.velocity)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> SetActorMotion:
        return cls(
            entity_runtime_id=r.varuint64(),
            velocity=r.vec3(),
            tick=r.varuint64(),
        )
