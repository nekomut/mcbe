"""Packet: MovementEffect."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOVEMENT_EFFECT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MovementEffect(Packet):
    packet_id = ID_MOVEMENT_EFFECT
    entity_runtime_id: int = 0
    type: int = 0
    duration: int = 0
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.varint32(self.type)
        w.varint32(self.duration)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> MovementEffect:
        return cls(
            entity_runtime_id=r.varuint64(),
            type=r.varint32(),
            duration=r.varint32(),
            tick=r.varuint64(),
        )
