"""Packet: ClientCheatAbility."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_CHEAT_ABILITY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientCheatAbility(Packet):
    packet_id = ID_CLIENT_CHEAT_ABILITY
    ability_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.ability_data)

    @classmethod
    def read(cls, r: PacketReader) -> ClientCheatAbility:
        return cls(
            ability_data=r.byte_slice(),
        )
