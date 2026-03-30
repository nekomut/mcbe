"""Packet: CameraShake."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_SHAKE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CameraShake(Packet):
    packet_id = ID_CAMERA_SHAKE
    intensity: float = 0.0
    duration: float = 0.0
    type: int = 0
    action: int = 0

    def write(self, w: PacketWriter) -> None:
        w.float32(self.intensity)
        w.float32(self.duration)
        w.uint8(self.type)
        w.uint8(self.action)

    @classmethod
    def read(cls, r: PacketReader) -> CameraShake:
        return cls(
            intensity=r.float32(),
            duration=r.float32(),
            type=r.uint8(),
            action=r.uint8(),
        )
