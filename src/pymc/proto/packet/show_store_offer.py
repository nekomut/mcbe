"""Packet: ShowStoreOffer."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SHOW_STORE_OFFER
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ShowStoreOffer(Packet):
    packet_id = ID_SHOW_STORE_OFFER
    offer_id: UUID = 0
    type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uuid(self.offer_id)
        w.uint8(self.type)

    @classmethod
    def read(cls, r: PacketReader) -> ShowStoreOffer:
        return cls(
            offer_id=r.uuid(),
            type=r.uint8(),
        )
