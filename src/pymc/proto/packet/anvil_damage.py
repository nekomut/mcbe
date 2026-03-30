"""Packet: AnvilDamage."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ANVIL_DAMAGE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class AnvilDamage(Packet):
    packet_id = ID_ANVIL_DAMAGE
    damage: int = 0
    anvil_position: BlockPos = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.damage)
        w.block_pos(self.anvil_position)

    @classmethod
    def read(cls, r: PacketReader) -> AnvilDamage:
        return cls(
            damage=r.uint8(),
            anvil_position=r.block_pos(),
        )
