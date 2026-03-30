"""Packet: UpdateSubChunkBlocks."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_SUB_CHUNK_BLOCKS
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class UpdateSubChunkBlocks(Packet):
    packet_id = ID_UPDATE_SUB_CHUNK_BLOCKS
    position: BlockPos = 0
    blocks: bytes = b""
    extra: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.byte_slice(self.blocks)
        w.byte_slice(self.extra)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateSubChunkBlocks:
        return cls(
            position=r.block_pos(),
            blocks=r.byte_slice(),
            extra=r.byte_slice(),
        )
