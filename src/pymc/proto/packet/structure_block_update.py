"""Packet: StructureBlockUpdate."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_STRUCTURE_BLOCK_UPDATE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class StructureBlockUpdate(Packet):
    packet_id = ID_STRUCTURE_BLOCK_UPDATE
    position: BlockPos = 0
    structure_name: str = ""
    filtered_structure_name: str = ""
    data_field: str = ""
    include_players: bool = False
    show_bounding_box: bool = False
    structure_block_type: int = 0
    settings: bytes = b""
    redstone_save_mode: int = 0
    should_trigger: bool = False
    waterlogged: bool = False

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.string(self.structure_name)
        w.string(self.filtered_structure_name)
        w.string(self.data_field)
        w.bool(self.include_players)
        w.bool(self.show_bounding_box)
        w.varint32(self.structure_block_type)
        w.byte_slice(self.settings)
        w.varint32(self.redstone_save_mode)
        w.bool(self.should_trigger)
        w.bool(self.waterlogged)

    @classmethod
    def read(cls, r: PacketReader) -> StructureBlockUpdate:
        return cls(
            position=r.block_pos(),
            structure_name=r.string(),
            filtered_structure_name=r.string(),
            data_field=r.string(),
            include_players=r.bool(),
            show_bounding_box=r.bool(),
            structure_block_type=r.varint32(),
            settings=r.byte_slice(),
            redstone_save_mode=r.varint32(),
            should_trigger=r.bool(),
            waterlogged=r.bool(),
        )
