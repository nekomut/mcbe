"""Packet: PlayerAction."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_ACTION
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class PlayerAction(Packet):
    packet_id = ID_PLAYER_ACTION
    entity_runtime_id: int = 0
    action_type: int = 0
    block_position: BlockPos = 0
    result_position: BlockPos = 0
    block_face: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.varint32(self.action_type)
        w.block_pos(self.block_position)
        w.block_pos(self.result_position)
        w.varint32(self.block_face)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerAction:
        return cls(
            entity_runtime_id=r.varuint64(),
            action_type=r.varint32(),
            block_position=r.block_pos(),
            result_position=r.block_pos(),
            block_face=r.varint32(),
        )
