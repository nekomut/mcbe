"""Packet: CompletedUsingItem."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_COMPLETED_USING_ITEM
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CompletedUsingItem(Packet):
    packet_id = ID_COMPLETED_USING_ITEM
    used_item_id: int = 0
    use_method: int = 0

    def write(self, w: PacketWriter) -> None:
        w.int16(self.used_item_id)
        w.int32(self.use_method)

    @classmethod
    def read(cls, r: PacketReader) -> CompletedUsingItem:
        return cls(
            used_item_id=r.int16(),
            use_method=r.int32(),
        )
