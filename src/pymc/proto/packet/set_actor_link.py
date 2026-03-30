"""Packet: SetActorLink."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_ACTOR_LINK
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetActorLink(Packet):
    packet_id = ID_SET_ACTOR_LINK
    entity_link: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.entity_link)

    @classmethod
    def read(cls, r: PacketReader) -> SetActorLink:
        return cls(
            entity_link=r.byte_slice(),
        )
