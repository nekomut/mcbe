"""Packet: RequestAbility."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REQUEST_ABILITY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class RequestAbility(Packet):
    packet_id = ID_REQUEST_ABILITY
    ability: int = 0
    value: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.ability)
        w.byte_slice(self.value)

    @classmethod
    def read(cls, r: PacketReader) -> RequestAbility:
        return cls(
            ability=r.varint32(),
            value=r.byte_slice(),
        )
