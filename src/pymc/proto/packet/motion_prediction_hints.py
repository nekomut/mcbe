"""Packet: MotionPredictionHints."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MOTION_PREDICTION_HINTS
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3


@register_server_packet
@dataclass
class MotionPredictionHints(Packet):
    packet_id = ID_MOTION_PREDICTION_HINTS
    entity_runtime_id: int = 0
    velocity: Vec3 = 0
    on_ground: bool = False

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.vec3(self.velocity)
        w.bool(self.on_ground)

    @classmethod
    def read(cls, r: PacketReader) -> MotionPredictionHints:
        return cls(
            entity_runtime_id=r.varuint64(),
            velocity=r.vec3(),
            on_ground=r.bool(),
        )
