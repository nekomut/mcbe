"""Packet: PlayerUpdateEntityOverrides."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_UPDATE_ENTITY_OVERRIDES
from pymc.proto.pool import Packet, register_server_packet

PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_CLEAR_ALL = 0
PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_REMOVE = 1
PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_INT = 2
PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_FLOAT = 3


@register_server_packet
@dataclass
class PlayerUpdateEntityOverrides(Packet):
    packet_id = ID_PLAYER_UPDATE_ENTITY_OVERRIDES
    entity_unique_id: int = 0
    property_index: int = 0
    type: int = 0
    int_value: int = 0
    float_value: float = 0.0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)
        w.varuint32(self.property_index)
        w.uint8(self.type)
        if self.type == PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_INT:
            w.int32(self.int_value)
        elif self.type == PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_FLOAT:
            w.float32(self.float_value)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerUpdateEntityOverrides:
        entity_unique_id = r.varint64()
        property_index = r.varuint32()
        type_ = r.uint8()
        int_value = 0
        float_value = 0.0
        if type_ == PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_INT:
            int_value = r.int32()
        elif type_ == PLAYER_UPDATE_ENTITY_OVERRIDES_TYPE_FLOAT:
            float_value = r.float32()
        return cls(
            entity_unique_id=entity_unique_id,
            property_index=property_index,
            type=type_,
            int_value=int_value,
            float_value=float_value,
        )
