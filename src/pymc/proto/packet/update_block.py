"""Packet: UpdateBlock."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_BLOCK
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class UpdateBlock(Packet):
    packet_id = ID_UPDATE_BLOCK
    position: BlockPos = 0
    new_block_runtime_id: int = 0
    flags: int = 0
    layer: int = 0

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.varuint32(self.new_block_runtime_id)
        w.varuint32(self.flags)
        w.varuint32(self.layer)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateBlock:
        return cls(
            position=r.block_pos(),
            new_block_runtime_id=r.varuint32(),
            flags=r.varuint32(),
            layer=r.varuint32(),
        )
