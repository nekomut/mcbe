"""Packet: ClientStartItemCooldown."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_START_ITEM_COOLDOWN
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientStartItemCooldown(Packet):
    packet_id = ID_CLIENT_START_ITEM_COOLDOWN
    category: str = ""
    duration: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.category)
        w.varint32(self.duration)

    @classmethod
    def read(cls, r: PacketReader) -> ClientStartItemCooldown:
        return cls(
            category=r.string(),
            duration=r.varint32(),
        )
