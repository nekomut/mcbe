"""Packet: RequestAbility."""

from __future__ import annotations

from dataclasses import dataclass

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_REQUEST_ABILITY
from mcbe.proto.pool import Packet, register_client_packet

# Value type constants.
ABILITY_VALUE_BOOL = 1
ABILITY_VALUE_FLOAT = 2


@register_client_packet
@dataclass
class RequestAbility(Packet):
    packet_id = ID_REQUEST_ABILITY
    ability: int = 0
    value_type: int = 0
    bool_value: bool = False
    float_value: float = 0.0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.ability)
        w.uint8(self.value_type)
        w.bool(self.bool_value)
        w.float32(self.float_value)

    @classmethod
    def read(cls, r: PacketReader) -> RequestAbility:
        return cls(
            ability=r.varint32(),
            value_type=r.uint8(),
            bool_value=r.bool(),
            float_value=r.float32(),
        )
