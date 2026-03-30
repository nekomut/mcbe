"""Packet: BlockPickRequest."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_BLOCK_PICK_REQUEST
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class BlockPickRequest(Packet):
    packet_id = ID_BLOCK_PICK_REQUEST
    position: BlockPos = 0
    add_block_nbt: bool = False
    hot_bar_slot: int = 0

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.bool(self.add_block_nbt)
        w.uint8(self.hot_bar_slot)

    @classmethod
    def read(cls, r: PacketReader) -> BlockPickRequest:
        return cls(
            position=r.block_pos(),
            add_block_nbt=r.bool(),
            hot_bar_slot=r.uint8(),
        )
