"""Packet: MovePlayer."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOVE_PLAYER
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3

# Movement modes
MOVE_MODE_NORMAL = 0
MOVE_MODE_RESET = 1
MOVE_MODE_TELEPORT = 2
MOVE_MODE_ROTATION = 3

# Teleport causes
TELEPORT_CAUSE_UNKNOWN = 0
TELEPORT_CAUSE_PROJECTILE = 1
TELEPORT_CAUSE_CHORUS_FRUIT = 2
TELEPORT_CAUSE_COMMAND = 3
TELEPORT_CAUSE_BEHAVIOUR = 4


@register_server_packet
@dataclass
class MovePlayer(Packet):
    packet_id = ID_MOVE_PLAYER
    entity_runtime_id: int = 0
    position: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))
    pitch: float = 0.0
    yaw: float = 0.0
    head_yaw: float = 0.0
    mode: int = 0
    on_ground: bool = False
    ridden_entity_runtime_id: int = 0
    teleport_cause: int = 0
    teleport_source_entity_type: int = 0
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.vec3(self.position)
        w.float32(self.pitch)
        w.float32(self.yaw)
        w.float32(self.head_yaw)
        w.uint8(self.mode)
        w.bool(self.on_ground)
        w.varuint64(self.ridden_entity_runtime_id)
        if self.mode == MOVE_MODE_TELEPORT:
            w.int32(self.teleport_cause)
            w.int32(self.teleport_source_entity_type)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> MovePlayer:
        entity_runtime_id = r.varuint64()
        position = r.vec3()
        pitch = r.float32()
        yaw = r.float32()
        head_yaw = r.float32()
        mode = r.uint8()
        on_ground = r.bool()
        ridden_entity_runtime_id = r.varuint64()
        teleport_cause = 0
        teleport_source_entity_type = 0
        if mode == MOVE_MODE_TELEPORT:
            teleport_cause = r.int32()
            teleport_source_entity_type = r.int32()
        tick = r.varuint64()
        return cls(
            entity_runtime_id=entity_runtime_id,
            position=position,
            pitch=pitch,
            yaw=yaw,
            head_yaw=head_yaw,
            mode=mode,
            on_ground=on_ground,
            ridden_entity_runtime_id=ridden_entity_runtime_id,
            teleport_cause=teleport_cause,
            teleport_source_entity_type=teleport_source_entity_type,
            tick=tick,
        )
