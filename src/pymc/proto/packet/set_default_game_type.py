"""Packet: SetDefaultGameType."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_DEFAULT_GAME_TYPE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetDefaultGameType(Packet):
    packet_id = ID_SET_DEFAULT_GAME_TYPE
    game_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.game_type)

    @classmethod
    def read(cls, r: PacketReader) -> SetDefaultGameType:
        return cls(
            game_type=r.varint32(),
        )
