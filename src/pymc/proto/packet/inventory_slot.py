"""Packet: InventorySlot."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_INVENTORY_SLOT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class InventorySlot(Packet):
    packet_id = ID_INVENTORY_SLOT
    window_id: int = 0
    slot: int = 0
    container: bytes = b""
    storage_item: bytes = b""
    new_item: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.window_id)
        w.varuint32(self.slot)
        w.byte_slice(self.container)
        w.byte_slice(self.storage_item)
        w.byte_slice(self.new_item)

    @classmethod
    def read(cls, r: PacketReader) -> InventorySlot:
        return cls(
            window_id=r.varuint32(),
            slot=r.varuint32(),
            container=r.byte_slice(),
            storage_item=r.byte_slice(),
            new_item=r.byte_slice(),
        )
