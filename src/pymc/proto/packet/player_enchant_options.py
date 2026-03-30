"""Packet: PlayerEnchantOptions."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_ENCHANT_OPTIONS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PlayerEnchantOptions(Packet):
    packet_id = ID_PLAYER_ENCHANT_OPTIONS
    options: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.options)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerEnchantOptions:
        return cls(
            options=r.byte_slice(),
        )
