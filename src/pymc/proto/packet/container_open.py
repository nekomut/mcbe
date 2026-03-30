"""Packet: ContainerOpen."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CONTAINER_OPEN
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class ContainerOpen(Packet):
    packet_id = ID_CONTAINER_OPEN
    window_id: int = 0
    container_type: int = 0
    container_position: BlockPos = 0
    container_entity_unique_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.window_id)
        w.uint8(self.container_type)
        w.block_pos(self.container_position)
        w.varint64(self.container_entity_unique_id)

    @classmethod
    def read(cls, r: PacketReader) -> ContainerOpen:
        return cls(
            window_id=r.uint8(),
            container_type=r.uint8(),
            container_position=r.block_pos(),
            container_entity_unique_id=r.varint64(),
        )
