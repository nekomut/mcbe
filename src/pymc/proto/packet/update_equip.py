"""Packet: UpdateEquip."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_EQUIP
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdateEquip(Packet):
    packet_id = ID_UPDATE_EQUIP
    window_id: int = 0
    window_type: int = 0
    size: int = 0
    entity_unique_id: int = 0
    serialised_inventory_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.window_id)
        w.uint8(self.window_type)
        w.varint32(self.size)
        w.varint64(self.entity_unique_id)
        w.bytes_raw(self.serialised_inventory_data)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateEquip:
        return cls(
            window_id=r.uint8(),
            window_type=r.uint8(),
            size=r.varint32(),
            entity_unique_id=r.varint64(),
            serialised_inventory_data=r.bytes_remaining(),
        )
