"""Packet: UnlockedRecipes."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UNLOCKED_RECIPES
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UnlockedRecipes(Packet):
    packet_id = ID_UNLOCKED_RECIPES
    unlock_type: int = 0
    recipes: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint32(self.unlock_type)
        w.byte_slice(self.recipes)

    @classmethod
    def read(cls, r: PacketReader) -> UnlockedRecipes:
        return cls(
            unlock_type=r.uint32(),
            recipes=r.byte_slice(),
        )
