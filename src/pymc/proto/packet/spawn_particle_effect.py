"""Packet: SpawnParticleEffect."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SPAWN_PARTICLE_EFFECT
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class SpawnParticleEffect(Packet):
    packet_id = ID_SPAWN_PARTICLE_EFFECT
    dimension: int = 0
    entity_unique_id: int = 0
    position: Vec3 = 0
    particle_name: str = ""
    mo_lang_variables: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.dimension)
        w.varint64(self.entity_unique_id)
        w.vec3(self.position)
        w.string(self.particle_name)
        w.byte_slice(self.mo_lang_variables)

    @classmethod
    def read(cls, r: PacketReader) -> SpawnParticleEffect:
        return cls(
            dimension=r.uint8(),
            entity_unique_id=r.varint64(),
            position=r.vec3(),
            particle_name=r.string(),
            mo_lang_variables=r.byte_slice(),
        )
