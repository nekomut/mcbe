"""Packet: PlayerLocation."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_LOCATION
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3

PLAYER_LOCATION_TYPE_COORDINATES = 0
PLAYER_LOCATION_TYPE_HIDE = 1


@register_server_packet
@dataclass
class PlayerLocation(Packet):
    packet_id = ID_PLAYER_LOCATION
    type: int = 0
    entity_unique_id: int = 0
    position: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))

    def write(self, w: PacketWriter) -> None:
        w.int32(self.type)
        w.varint64(self.entity_unique_id)
        if self.type == PLAYER_LOCATION_TYPE_COORDINATES:
            w.vec3(self.position)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerLocation:
        type_ = r.int32()
        entity_unique_id = r.varint64()
        position = Vec3(0.0, 0.0, 0.0)
        if type_ == PLAYER_LOCATION_TYPE_COORDINATES:
            position = r.vec3()
        return cls(
            type=type_,
            entity_unique_id=entity_unique_id,
            position=position,
        )
