"""Packet: CameraSpline."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_SPLINE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CameraSpline(Packet):
    packet_id = ID_CAMERA_SPLINE
    splines: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.splines)

    @classmethod
    def read(cls, r: PacketReader) -> CameraSpline:
        return cls(
            splines=r.byte_slice(),
        )
