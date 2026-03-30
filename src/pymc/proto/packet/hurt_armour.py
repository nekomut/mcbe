"""Packet: HurtArmour."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_HURT_ARMOUR
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class HurtArmour(Packet):
    packet_id = ID_HURT_ARMOUR
    cause: int = 0
    damage: int = 0
    armour_slots: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.cause)
        w.varint32(self.damage)
        w.varint64(self.armour_slots)

    @classmethod
    def read(cls, r: PacketReader) -> HurtArmour:
        return cls(
            cause=r.varint32(),
            damage=r.varint32(),
            armour_slots=r.varint64(),
        )
