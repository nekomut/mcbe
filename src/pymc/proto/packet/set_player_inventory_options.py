"""Packet: SetPlayerInventoryOptions."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_PLAYER_INVENTORY_OPTIONS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetPlayerInventoryOptions(Packet):
    packet_id = ID_SET_PLAYER_INVENTORY_OPTIONS
    left_inventory_tab: int = 0
    right_inventory_tab: int = 0
    filtering: bool = False
    inventory_layout: int = 0
    crafting_layout: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.left_inventory_tab)
        w.varint32(self.right_inventory_tab)
        w.bool(self.filtering)
        w.varint32(self.inventory_layout)
        w.varint32(self.crafting_layout)

    @classmethod
    def read(cls, r: PacketReader) -> SetPlayerInventoryOptions:
        return cls(
            left_inventory_tab=r.varint32(),
            right_inventory_tab=r.varint32(),
            filtering=r.bool(),
            inventory_layout=r.varint32(),
            crafting_layout=r.varint32(),
        )
