"""Packet: ShowCredits."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SHOW_CREDITS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ShowCredits(Packet):
    packet_id = ID_SHOW_CREDITS
    player_runtime_id: int = 0
    status_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.player_runtime_id)
        w.varint32(self.status_type)

    @classmethod
    def read(cls, r: PacketReader) -> ShowCredits:
        return cls(
            player_runtime_id=r.varuint64(),
            status_type=r.varint32(),
        )
