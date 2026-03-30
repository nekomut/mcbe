"""Packet: SimpleEvent."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SIMPLE_EVENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SimpleEvent(Packet):
    packet_id = ID_SIMPLE_EVENT
    event_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint16(self.event_type)

    @classmethod
    def read(cls, r: PacketReader) -> SimpleEvent:
        return cls(
            event_type=r.uint16(),
        )
