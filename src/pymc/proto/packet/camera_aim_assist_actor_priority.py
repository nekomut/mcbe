"""Packet: CameraAimAssistActorPriority."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CAMERA_AIM_ASSIST_ACTOR_PRIORITY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CameraAimAssistActorPriority(Packet):
    packet_id = ID_CAMERA_AIM_ASSIST_ACTOR_PRIORITY
    priority_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.priority_data)

    @classmethod
    def read(cls, r: PacketReader) -> CameraAimAssistActorPriority:
        return cls(
            priority_data=r.byte_slice(),
        )
