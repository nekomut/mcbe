"""Packet: LevelSoundEvent."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LEVEL_SOUND_EVENT
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class LevelSoundEvent(Packet):
    packet_id = ID_LEVEL_SOUND_EVENT
    sound_type: int = 0
    position: Vec3 = 0
    extra_data: int = 0
    entity_type: str = ""
    baby_mob: bool = False
    disable_relative_volume: bool = False
    entity_unique_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.sound_type)
        w.vec3(self.position)
        w.varint32(self.extra_data)
        w.string(self.entity_type)
        w.bool(self.baby_mob)
        w.bool(self.disable_relative_volume)
        w.int64(self.entity_unique_id)

    @classmethod
    def read(cls, r: PacketReader) -> LevelSoundEvent:
        return cls(
            sound_type=r.varuint32(),
            position=r.vec3(),
            extra_data=r.varint32(),
            entity_type=r.string(),
            baby_mob=r.bool(),
            disable_relative_volume=r.bool(),
            entity_unique_id=r.int64(),
        )
