"""Packet: LecternUpdate."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LECTERN_UPDATE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class LecternUpdate(Packet):
    packet_id = ID_LECTERN_UPDATE
    page: int = 0
    page_count: int = 0
    position: BlockPos = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.page)
        w.uint8(self.page_count)
        w.block_pos(self.position)

    @classmethod
    def read(cls, r: PacketReader) -> LecternUpdate:
        return cls(
            page=r.uint8(),
            page_count=r.uint8(),
            position=r.block_pos(),
        )
