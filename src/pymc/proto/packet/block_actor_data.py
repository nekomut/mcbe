"""Packet: BlockActorData."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_BLOCK_ACTOR_DATA
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class BlockActorData(Packet):
    packet_id = ID_BLOCK_ACTOR_DATA
    position: BlockPos = 0
    nbt_data: dict = field(default_factory=dict)

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.nbt(self.nbt_data)

    @classmethod
    def read(cls, r: PacketReader) -> BlockActorData:
        return cls(
            position=r.block_pos(),
            nbt_data=r.nbt(),
        )
