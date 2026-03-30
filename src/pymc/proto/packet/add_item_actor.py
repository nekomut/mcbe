"""Packet: AddItemActor."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADD_ITEM_ACTOR
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class AddItemActor(Packet):
    packet_id = ID_ADD_ITEM_ACTOR
    entity_unique_id: int = 0
    entity_runtime_id: int = 0
    item: bytes = b""
    position: Vec3 = 0
    velocity: Vec3 = 0
    entity_metadata: bytes = b""
    from_fishing: bool = False

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)
        w.varuint64(self.entity_runtime_id)
        w.byte_slice(self.item)
        w.vec3(self.position)
        w.vec3(self.velocity)
        w.byte_slice(self.entity_metadata)
        w.bool(self.from_fishing)

    @classmethod
    def read(cls, r: PacketReader) -> AddItemActor:
        return cls(
            entity_unique_id=r.varint64(),
            entity_runtime_id=r.varuint64(),
            item=r.byte_slice(),
            position=r.vec3(),
            velocity=r.vec3(),
            entity_metadata=r.byte_slice(),
            from_fishing=r.bool(),
        )
