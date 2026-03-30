"""Packet: CameraAimAssistPresets."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_AIM_ASSIST_PRESETS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CameraAimAssistPresets(Packet):
    packet_id = ID_CAMERA_AIM_ASSIST_PRESETS
    categories: bytes = b""
    presets: bytes = b""
    operation: int = 0

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.categories)
        w.byte_slice(self.presets)
        w.uint8(self.operation)

    @classmethod
    def read(cls, r: PacketReader) -> CameraAimAssistPresets:
        return cls(
            categories=r.byte_slice(),
            presets=r.byte_slice(),
            operation=r.uint8(),
        )
