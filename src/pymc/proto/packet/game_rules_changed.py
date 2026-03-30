"""Packet: GameRulesChanged."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_GAME_RULES_CHANGED
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class GameRulesChanged(Packet):
    packet_id = ID_GAME_RULES_CHANGED
    game_rules: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.game_rules)

    @classmethod
    def read(cls, r: PacketReader) -> GameRulesChanged:
        return cls(
            game_rules=r.byte_slice(),
        )
