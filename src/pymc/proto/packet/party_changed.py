"""Packet: PartyChanged."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PARTY_CHANGED
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PartyChanged(Packet):
    packet_id = ID_PARTY_CHANGED
    party_id: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.party_id)

    @classmethod
    def read(cls, r: PacketReader) -> PartyChanged:
        return cls(
            party_id=r.string(),
        )
