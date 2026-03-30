"""Packet: GUIDataPickItem."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_GUI_DATA_PICK_ITEM
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class GUIDataPickItem(Packet):
    packet_id = ID_GUI_DATA_PICK_ITEM
    item_name: str = ""
    item_effects: str = ""
    hot_bar_slot: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.item_name)
        w.string(self.item_effects)
        w.int32(self.hot_bar_slot)

    @classmethod
    def read(cls, r: PacketReader) -> GUIDataPickItem:
        return cls(
            item_name=r.string(),
            item_effects=r.string(),
            hot_bar_slot=r.int32(),
        )
