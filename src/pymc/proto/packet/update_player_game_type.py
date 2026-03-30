"""Packet: UpdatePlayerGameType."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_PLAYER_GAME_TYPE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdatePlayerGameType(Packet):
    packet_id = ID_UPDATE_PLAYER_GAME_TYPE
    game_type: int = 0
    player_unique_id: int = 0
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.game_type)
        w.varint64(self.player_unique_id)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> UpdatePlayerGameType:
        return cls(
            game_type=r.varint32(),
            player_unique_id=r.varint64(),
            tick=r.varuint64(),
        )
