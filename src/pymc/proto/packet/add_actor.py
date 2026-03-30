"""Packet: AddActor."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADD_ACTOR
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class AddActor(Packet):
    packet_id = ID_ADD_ACTOR
    entity_unique_id: int = 0
    entity_runtime_id: int = 0
    entity_type: str = ""
    position: Vec3 = 0
    velocity: Vec3 = 0
    pitch: float = 0.0
    yaw: float = 0.0
    head_yaw: float = 0.0
    body_yaw: float = 0.0
    attributes: bytes = b""
    entity_metadata: bytes = b""
    entity_properties: bytes = b""
    entity_links: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)
        w.varuint64(self.entity_runtime_id)
        w.string(self.entity_type)
        w.vec3(self.position)
        w.vec3(self.velocity)
        w.float32(self.pitch)
        w.float32(self.yaw)
        w.float32(self.head_yaw)
        w.float32(self.body_yaw)
        w.byte_slice(self.attributes)
        w.byte_slice(self.entity_metadata)
        w.byte_slice(self.entity_properties)
        w.byte_slice(self.entity_links)

    @classmethod
    def read(cls, r: PacketReader) -> AddActor:
        return cls(
            entity_unique_id=r.varint64(),
            entity_runtime_id=r.varuint64(),
            entity_type=r.string(),
            position=r.vec3(),
            velocity=r.vec3(),
            pitch=r.float32(),
            yaw=r.float32(),
            head_yaw=r.float32(),
            body_yaw=r.float32(),
            attributes=r.byte_slice(),
            entity_metadata=r.byte_slice(),
            entity_properties=r.byte_slice(),
            entity_links=r.byte_slice(),
        )
