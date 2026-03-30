"""Packet: ChangeDimension."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CHANGE_DIMENSION
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class ChangeDimension(Packet):
    packet_id = ID_CHANGE_DIMENSION
    dimension: int = 0
    position: Vec3 = 0
    respawn: bool = False
    loading_screen_id: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.dimension)
        w.vec3(self.position)
        w.bool(self.respawn)
        w.byte_slice(self.loading_screen_id)

    @classmethod
    def read(cls, r: PacketReader) -> ChangeDimension:
        return cls(
            dimension=r.varint32(),
            position=r.vec3(),
            respawn=r.bool(),
            loading_screen_id=r.byte_slice(),
        )
