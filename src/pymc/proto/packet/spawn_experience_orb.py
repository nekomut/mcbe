"""Packet: SpawnExperienceOrb."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SPAWN_EXPERIENCE_ORB
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class SpawnExperienceOrb(Packet):
    packet_id = ID_SPAWN_EXPERIENCE_ORB
    position: Vec3 = 0
    experience_amount: int = 0

    def write(self, w: PacketWriter) -> None:
        w.vec3(self.position)
        w.varint32(self.experience_amount)

    @classmethod
    def read(cls, r: PacketReader) -> SpawnExperienceOrb:
        return cls(
            position=r.vec3(),
            experience_amount=r.varint32(),
        )
