"""Packet: BlockEvent."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_BLOCK_EVENT
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class BlockEvent(Packet):
    packet_id = ID_BLOCK_EVENT
    position: BlockPos = 0
    event_type: int = 0
    event_data: int = 0

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.varint32(self.event_type)
        w.varint32(self.event_data)

    @classmethod
    def read(cls, r: PacketReader) -> BlockEvent:
        return cls(
            position=r.block_pos(),
            event_type=r.varint32(),
            event_data=r.varint32(),
        )
