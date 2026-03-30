"""Packet: AwardAchievement."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_AWARD_ACHIEVEMENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AwardAchievement(Packet):
    packet_id = ID_AWARD_ACHIEVEMENT
    achievement_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.int32(self.achievement_id)

    @classmethod
    def read(cls, r: PacketReader) -> AwardAchievement:
        return cls(
            achievement_id=r.int32(),
        )
