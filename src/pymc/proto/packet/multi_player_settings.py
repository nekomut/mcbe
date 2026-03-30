"""Packet: MultiPlayerSettings."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MULTI_PLAYER_SETTINGS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MultiPlayerSettings(Packet):
    packet_id = ID_MULTI_PLAYER_SETTINGS
    action_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.action_type)

    @classmethod
    def read(cls, r: PacketReader) -> MultiPlayerSettings:
        return cls(
            action_type=r.varint32(),
        )
