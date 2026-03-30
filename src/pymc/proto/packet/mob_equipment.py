"""Packet: MobEquipment."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOB_EQUIPMENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MobEquipment(Packet):
    packet_id = ID_MOB_EQUIPMENT
    entity_runtime_id: int = 0
    new_item: bytes = b""
    inventory_slot: int = 0
    hot_bar_slot: int = 0
    window_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.byte_slice(self.new_item)
        w.uint8(self.inventory_slot)
        w.uint8(self.hot_bar_slot)
        w.uint8(self.window_id)

    @classmethod
    def read(cls, r: PacketReader) -> MobEquipment:
        return cls(
            entity_runtime_id=r.varuint64(),
            new_item=r.byte_slice(),
            inventory_slot=r.uint8(),
            hot_bar_slot=r.uint8(),
            window_id=r.uint8(),
        )
