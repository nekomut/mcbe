"""Packet: LessonProgress."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LESSON_PROGRESS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class LessonProgress(Packet):
    packet_id = ID_LESSON_PROGRESS
    identifier: str = ""
    action: int = 0
    score: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.identifier)
        w.varint32(self.action)
        w.varint32(self.score)

    @classmethod
    def read(cls, r: PacketReader) -> LessonProgress:
        return cls(
            identifier=r.string(),
            action=r.varint32(),
            score=r.varint32(),
        )
