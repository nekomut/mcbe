"""Packet: UpdateTrade."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_TRADE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdateTrade(Packet):
    packet_id = ID_UPDATE_TRADE
    window_id: int = 0
    window_type: int = 0
    size: int = 0
    trade_tier: int = 0
    villager_unique_id: int = 0
    entity_unique_id: int = 0
    display_name: str = ""
    new_trade_ui: bool = False
    demand_based_prices: bool = False
    serialised_offers: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.window_id)
        w.uint8(self.window_type)
        w.varint32(self.size)
        w.varint32(self.trade_tier)
        w.varint64(self.villager_unique_id)
        w.varint64(self.entity_unique_id)
        w.string(self.display_name)
        w.bool(self.new_trade_ui)
        w.bool(self.demand_based_prices)
        w.bytes_raw(self.serialised_offers)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateTrade:
        return cls(
            window_id=r.uint8(),
            window_type=r.uint8(),
            size=r.varint32(),
            trade_tier=r.varint32(),
            villager_unique_id=r.varint64(),
            entity_unique_id=r.varint64(),
            display_name=r.string(),
            new_trade_ui=r.bool(),
            demand_based_prices=r.bool(),
            serialised_offers=r.bytes_remaining(),
        )
