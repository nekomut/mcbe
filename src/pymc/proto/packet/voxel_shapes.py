"""Packet: VoxelShapes."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_VOXEL_SHAPES
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class VoxelShapes(Packet):
    packet_id = ID_VOXEL_SHAPES
    shapes: bytes = b""
    name_map: bytes = b""
    custom_shape_count: int = 0

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.shapes)
        w.byte_slice(self.name_map)
        w.uint16(self.custom_shape_count)

    @classmethod
    def read(cls, r: PacketReader) -> VoxelShapes:
        return cls(
            shapes=r.byte_slice(),
            name_map=r.byte_slice(),
            custom_shape_count=r.uint16(),
        )
