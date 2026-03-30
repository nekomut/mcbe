"""Packet: RemoveActor."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REMOVE_ACTOR
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class RemoveActor(Packet):
    packet_id = ID_REMOVE_ACTOR
    entity_unique_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)

    @classmethod
    def read(cls, r: PacketReader) -> RemoveActor:
        return cls(
            entity_unique_id=r.varint64(),
        )
