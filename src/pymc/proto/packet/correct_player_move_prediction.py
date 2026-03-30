"""Packet: CorrectPlayerMovePrediction."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CORRECT_PLAYER_MOVE_PREDICTION
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec2, Vec3


@register_server_packet
@dataclass
class CorrectPlayerMovePrediction(Packet):
    packet_id = ID_CORRECT_PLAYER_MOVE_PREDICTION
    prediction_type: int = 0
    position: Vec3 = 0
    delta: Vec3 = 0
    rotation: Vec2 = 0
    vehicle_angular_velocity: bytes = b""
    on_ground: bool = False
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.prediction_type)
        w.vec3(self.position)
        w.vec3(self.delta)
        w.vec2(self.rotation)
        w.byte_slice(self.vehicle_angular_velocity)
        w.bool(self.on_ground)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> CorrectPlayerMovePrediction:
        return cls(
            prediction_type=r.uint8(),
            position=r.vec3(),
            delta=r.vec3(),
            rotation=r.vec2(),
            vehicle_angular_velocity=r.byte_slice(),
            on_ground=r.bool(),
            tick=r.varuint64(),
        )
