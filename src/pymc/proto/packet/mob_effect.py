"""Packet: MobEffect."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOB_EFFECT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MobEffect(Packet):
    packet_id = ID_MOB_EFFECT
    entity_runtime_id: int = 0
    operation: int = 0
    effect_type: int = 0
    amplifier: int = 0
    particles: bool = False
    duration: int = 0
    tick: int = 0
    ambient: bool = False

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.uint8(self.operation)
        w.varint32(self.effect_type)
        w.varint32(self.amplifier)
        w.bool(self.particles)
        w.varint32(self.duration)
        w.varuint64(self.tick)
        w.bool(self.ambient)

    @classmethod
    def read(cls, r: PacketReader) -> MobEffect:
        return cls(
            entity_runtime_id=r.varuint64(),
            operation=r.uint8(),
            effect_type=r.varint32(),
            amplifier=r.varint32(),
            particles=r.bool(),
            duration=r.varint32(),
            tick=r.varuint64(),
            ambient=r.bool(),
        )
