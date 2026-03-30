"""Packet: PlayerFog."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_FOG
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PlayerFog(Packet):
    packet_id = ID_PLAYER_FOG
    stack: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.stack)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerFog:
        return cls(
            stack=r.byte_slice(),
        )
