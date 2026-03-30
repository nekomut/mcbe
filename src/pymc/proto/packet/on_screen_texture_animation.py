"""Packet: OnScreenTextureAnimation."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ON_SCREEN_TEXTURE_ANIMATION
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class OnScreenTextureAnimation(Packet):
    packet_id = ID_ON_SCREEN_TEXTURE_ANIMATION
    animation_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint32(self.animation_type)

    @classmethod
    def read(cls, r: PacketReader) -> OnScreenTextureAnimation:
        return cls(
            animation_type=r.uint32(),
        )
