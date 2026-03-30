"""Packet: StopSound."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_STOP_SOUND
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class StopSound(Packet):
    packet_id = ID_STOP_SOUND
    sound_name: str = ""
    stop_all: bool = False
    stop_music_legacy: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.sound_name)
        w.bool(self.stop_all)
        w.bool(self.stop_music_legacy)

    @classmethod
    def read(cls, r: PacketReader) -> StopSound:
        return cls(
            sound_name=r.string(),
            stop_all=r.bool(),
            stop_music_legacy=r.bool(),
        )
