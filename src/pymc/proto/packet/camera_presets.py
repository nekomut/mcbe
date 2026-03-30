"""Packet: CameraPresets."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_PRESETS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CameraPresets(Packet):
    packet_id = ID_CAMERA_PRESETS
    presets: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.presets)

    @classmethod
    def read(cls, r: PacketReader) -> CameraPresets:
        return cls(
            presets=r.byte_slice(),
        )
