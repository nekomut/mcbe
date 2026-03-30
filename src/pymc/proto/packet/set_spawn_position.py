"""Packet: SetSpawnPosition."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_SPAWN_POSITION
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class SetSpawnPosition(Packet):
    packet_id = ID_SET_SPAWN_POSITION
    spawn_type: int = 0
    position: BlockPos = 0
    dimension: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.spawn_type)
        w.block_pos(self.position)
        w.varint32(self.dimension)

    @classmethod
    def read(cls, r: PacketReader) -> SetSpawnPosition:
        return cls(
            spawn_type=r.varint32(),
            position=r.block_pos(),
            dimension=r.varint32(),
        )
