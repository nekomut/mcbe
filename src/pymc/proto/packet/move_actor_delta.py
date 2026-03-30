"""Packet: MoveActorDelta."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOVE_ACTOR_DELTA
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3

MOVE_ACTOR_DELTA_FLAG_HAS_X = 1 << 0
MOVE_ACTOR_DELTA_FLAG_HAS_Y = 1 << 1
MOVE_ACTOR_DELTA_FLAG_HAS_Z = 1 << 2
MOVE_ACTOR_DELTA_FLAG_HAS_ROT_X = 1 << 3
MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Y = 1 << 4
MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Z = 1 << 5
MOVE_ACTOR_DELTA_FLAG_ON_GROUND = 1 << 6
MOVE_ACTOR_DELTA_FLAG_TELEPORT = 1 << 7
MOVE_ACTOR_DELTA_FLAG_FORCE_MOVE = 1 << 8


@register_server_packet
@dataclass
class MoveActorDelta(Packet):
    packet_id = ID_MOVE_ACTOR_DELTA
    entity_runtime_id: int = 0
    flags: int = 0
    position: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))
    rotation: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.uint16(self.flags)
        if self.flags & MOVE_ACTOR_DELTA_FLAG_HAS_X:
            w.float32(self.position.x)
        if self.flags & MOVE_ACTOR_DELTA_FLAG_HAS_Y:
            w.float32(self.position.y)
        if self.flags & MOVE_ACTOR_DELTA_FLAG_HAS_Z:
            w.float32(self.position.z)
        if self.flags & MOVE_ACTOR_DELTA_FLAG_HAS_ROT_X:
            w.byte_float(self.rotation.x)
        if self.flags & MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Y:
            w.byte_float(self.rotation.y)
        if self.flags & MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Z:
            w.byte_float(self.rotation.z)

    @classmethod
    def read(cls, r: PacketReader) -> MoveActorDelta:
        entity_runtime_id = r.varuint64()
        flags = r.uint16()
        px = r.float32() if flags & MOVE_ACTOR_DELTA_FLAG_HAS_X else 0.0
        py = r.float32() if flags & MOVE_ACTOR_DELTA_FLAG_HAS_Y else 0.0
        pz = r.float32() if flags & MOVE_ACTOR_DELTA_FLAG_HAS_Z else 0.0
        rx = r.byte_float() if flags & MOVE_ACTOR_DELTA_FLAG_HAS_ROT_X else 0.0
        ry = r.byte_float() if flags & MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Y else 0.0
        rz = r.byte_float() if flags & MOVE_ACTOR_DELTA_FLAG_HAS_ROT_Z else 0.0
        return cls(
            entity_runtime_id=entity_runtime_id,
            flags=flags,
            position=Vec3(px, py, pz),
            rotation=Vec3(rx, ry, rz),
        )
