"""Packet: OpenSign."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_OPEN_SIGN
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class OpenSign(Packet):
    packet_id = ID_OPEN_SIGN
    position: BlockPos = 0
    front_side: bool = False

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.bool(self.front_side)

    @classmethod
    def read(cls, r: PacketReader) -> OpenSign:
        return cls(
            position=r.block_pos(),
            front_side=r.bool(),
        )
