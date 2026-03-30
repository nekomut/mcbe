"""Packet: SetHealth."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_HEALTH
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetHealth(Packet):
    packet_id = ID_SET_HEALTH
    health: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.health)

    @classmethod
    def read(cls, r: PacketReader) -> SetHealth:
        return cls(
            health=r.varint32(),
        )
