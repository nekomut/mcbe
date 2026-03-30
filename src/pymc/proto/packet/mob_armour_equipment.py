"""Packet: MobArmourEquipment."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOB_ARMOUR_EQUIPMENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MobArmourEquipment(Packet):
    packet_id = ID_MOB_ARMOUR_EQUIPMENT
    entity_runtime_id: int = 0
    helmet: bytes = b""
    chestplate: bytes = b""
    leggings: bytes = b""
    boots: bytes = b""
    body: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.byte_slice(self.helmet)
        w.byte_slice(self.chestplate)
        w.byte_slice(self.leggings)
        w.byte_slice(self.boots)
        w.byte_slice(self.body)

    @classmethod
    def read(cls, r: PacketReader) -> MobArmourEquipment:
        return cls(
            entity_runtime_id=r.varuint64(),
            helmet=r.byte_slice(),
            chestplate=r.byte_slice(),
            leggings=r.byte_slice(),
            boots=r.byte_slice(),
            body=r.byte_slice(),
        )
