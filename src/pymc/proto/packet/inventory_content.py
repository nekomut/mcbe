"""Packet: InventoryContent."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_INVENTORY_CONTENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class InventoryContent(Packet):
    packet_id = ID_INVENTORY_CONTENT
    window_id: int = 0
    content: bytes = b""
    container: bytes = b""
    storage_item: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.window_id)
        w.byte_slice(self.content)
        w.byte_slice(self.container)
        w.byte_slice(self.storage_item)

    @classmethod
    def read(cls, r: PacketReader) -> InventoryContent:
        return cls(
            window_id=r.varuint32(),
            content=r.byte_slice(),
            container=r.byte_slice(),
            storage_item=r.byte_slice(),
        )
