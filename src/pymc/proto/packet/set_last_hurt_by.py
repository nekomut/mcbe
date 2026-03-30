"""Packet: SetLastHurtBy."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_LAST_HURT_BY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetLastHurtBy(Packet):
    packet_id = ID_SET_LAST_HURT_BY
    entity_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.entity_type)

    @classmethod
    def read(cls, r: PacketReader) -> SetLastHurtBy:
        return cls(
            entity_type=r.varint32(),
        )
