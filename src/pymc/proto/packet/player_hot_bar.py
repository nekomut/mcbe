"""Packet: PlayerHotBar."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_HOT_BAR
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PlayerHotBar(Packet):
    packet_id = ID_PLAYER_HOT_BAR
    selected_hot_bar_slot: int = 0
    window_id: int = 0
    select_hot_bar_slot: bool = False

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.selected_hot_bar_slot)
        w.uint8(self.window_id)
        w.bool(self.select_hot_bar_slot)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerHotBar:
        return cls(
            selected_hot_bar_slot=r.varuint32(),
            window_id=r.uint8(),
            select_hot_bar_slot=r.bool(),
        )
