"""Packet: ItemRegistry."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ITEM_REGISTRY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ItemRegistry(Packet):
    packet_id = ID_ITEM_REGISTRY
    items: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.items)

    @classmethod
    def read(cls, r: PacketReader) -> ItemRegistry:
        return cls(
            items=r.byte_slice(),
        )
