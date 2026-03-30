"""Packet: ActorEvent."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ACTOR_EVENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ActorEvent(Packet):
    packet_id = ID_ACTOR_EVENT
    entity_runtime_id: int = 0
    event_type: int = 0
    event_data: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.uint8(self.event_type)
        w.varint32(self.event_data)

    @classmethod
    def read(cls, r: PacketReader) -> ActorEvent:
        return cls(
            entity_runtime_id=r.varuint64(),
            event_type=r.uint8(),
            event_data=r.varint32(),
        )
