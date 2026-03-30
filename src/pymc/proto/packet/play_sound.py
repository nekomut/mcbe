"""Packet: PlaySound."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAY_SOUND
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class PlaySound(Packet):
    packet_id = ID_PLAY_SOUND
    sound_name: str = ""
    position: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))
    volume: float = 0.0
    pitch: float = 0.0

    def write(self, w: PacketWriter) -> None:
        w.string(self.sound_name)
        w.vec3(self.position)
        w.float32(self.volume)
        w.float32(self.pitch)

    @classmethod
    def read(cls, r: PacketReader) -> PlaySound:
        return cls(
            sound_name=r.string(),
            position=r.vec3(),
            volume=r.float32(),
            pitch=r.float32(),
        )
