"""Packet: ClientCameraAimAssist."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_CAMERA_AIM_ASSIST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientCameraAimAssist(Packet):
    packet_id = ID_CLIENT_CAMERA_AIM_ASSIST
    preset_id: str = ""
    action: int = 0
    allow_aim_assist: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.preset_id)
        w.uint8(self.action)
        w.bool(self.allow_aim_assist)

    @classmethod
    def read(cls, r: PacketReader) -> ClientCameraAimAssist:
        return cls(
            preset_id=r.string(),
            action=r.uint8(),
            allow_aim_assist=r.bool(),
        )
