"""Packet: CameraAimAssist."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_AIM_ASSIST
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec2


@register_server_packet
@dataclass
class CameraAimAssist(Packet):
    packet_id = ID_CAMERA_AIM_ASSIST
    preset: str = ""
    angle: Vec2 = 0
    distance: float = 0.0
    target_mode: int = 0
    action: int = 0
    show_debug_render: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.preset)
        w.vec2(self.angle)
        w.float32(self.distance)
        w.uint8(self.target_mode)
        w.uint8(self.action)
        w.bool(self.show_debug_render)

    @classmethod
    def read(cls, r: PacketReader) -> CameraAimAssist:
        return cls(
            preset=r.string(),
            angle=r.vec2(),
            distance=r.float32(),
            target_mode=r.uint8(),
            action=r.uint8(),
            show_debug_render=r.bool(),
        )
