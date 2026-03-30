"""Packet: LabTable."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LAB_TABLE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class LabTable(Packet):
    packet_id = ID_LAB_TABLE
    action_type: int = 0
    position: BlockPos = 0
    reaction_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_type)
        w.block_pos(self.position)
        w.uint8(self.reaction_type)

    @classmethod
    def read(cls, r: PacketReader) -> LabTable:
        return cls(
            action_type=r.uint8(),
            position=r.block_pos(),
            reaction_type=r.uint8(),
        )
