"""Packet: LevelEvent."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LEVEL_EVENT
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class LevelEvent(Packet):
    packet_id = ID_LEVEL_EVENT
    event_type: int = 0
    position: Vec3 = 0
    event_data: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.event_type)
        w.vec3(self.position)
        w.varint32(self.event_data)

    @classmethod
    def read(cls, r: PacketReader) -> LevelEvent:
        return cls(
            event_type=r.varint32(),
            position=r.vec3(),
            event_data=r.varint32(),
        )
