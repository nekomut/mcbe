"""Packet: DebugInfo."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_DEBUG_INFO
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class DebugInfo(Packet):
    packet_id = ID_DEBUG_INFO
    player_unique_id: int = 0
    data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.player_unique_id)
        w.byte_slice(self.data)

    @classmethod
    def read(cls, r: PacketReader) -> DebugInfo:
        return cls(
            player_unique_id=r.varint64(),
            data=r.byte_slice(),
        )
