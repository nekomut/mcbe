"""Packet: CraftingData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CRAFTING_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CraftingData(Packet):
    packet_id = ID_CRAFTING_DATA
    recipes: bytes = b""
    potion_recipes: bytes = b""
    potion_container_change_recipes: bytes = b""
    material_reducers: bytes = b""
    clear_recipes: bool = False

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.recipes)
        w.byte_slice(self.potion_recipes)
        w.byte_slice(self.potion_container_change_recipes)
        w.byte_slice(self.material_reducers)
        w.bool(self.clear_recipes)

    @classmethod
    def read(cls, r: PacketReader) -> CraftingData:
        return cls(
            recipes=r.byte_slice(),
            potion_recipes=r.byte_slice(),
            potion_container_change_recipes=r.byte_slice(),
            material_reducers=r.byte_slice(),
            clear_recipes=r.bool(),
        )
