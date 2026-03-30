"""Packet: AddPlayer."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADD_PLAYER
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class AddPlayer(Packet):
    packet_id = ID_ADD_PLAYER
    uuid: UUID = 0
    username: str = ""
    entity_runtime_id: int = 0
    platform_chat_id: str = ""
    position: Vec3 = 0
    velocity: Vec3 = 0
    pitch: float = 0.0
    yaw: float = 0.0
    head_yaw: float = 0.0
    held_item: bytes = b""
    game_type: int = 0
    entity_metadata: bytes = b""
    entity_properties: bytes = b""
    ability_data: bytes = b""
    entity_links: bytes = b""
    device_id: str = ""
    build_platform: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uuid(self.uuid)
        w.string(self.username)
        w.varuint64(self.entity_runtime_id)
        w.string(self.platform_chat_id)
        w.vec3(self.position)
        w.vec3(self.velocity)
        w.float32(self.pitch)
        w.float32(self.yaw)
        w.float32(self.head_yaw)
        w.byte_slice(self.held_item)
        w.varint32(self.game_type)
        w.byte_slice(self.entity_metadata)
        w.byte_slice(self.entity_properties)
        w.byte_slice(self.ability_data)
        w.byte_slice(self.entity_links)
        w.string(self.device_id)
        w.int32(self.build_platform)

    @classmethod
    def read(cls, r: PacketReader) -> AddPlayer:
        return cls(
            uuid=r.uuid(),
            username=r.string(),
            entity_runtime_id=r.varuint64(),
            platform_chat_id=r.string(),
            position=r.vec3(),
            velocity=r.vec3(),
            pitch=r.float32(),
            yaw=r.float32(),
            head_yaw=r.float32(),
            held_item=r.byte_slice(),
            game_type=r.varint32(),
            entity_metadata=r.byte_slice(),
            entity_properties=r.byte_slice(),
            ability_data=r.byte_slice(),
            entity_links=r.byte_slice(),
            device_id=r.string(),
            build_platform=r.int32(),
        )
