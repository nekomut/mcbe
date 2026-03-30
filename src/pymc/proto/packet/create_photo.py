"""Packet: CreatePhoto."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CREATE_PHOTO
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CreatePhoto(Packet):
    packet_id = ID_CREATE_PHOTO
    entity_unique_id: int = 0
    photo_name: str = ""
    item_name: str = ""

    def write(self, w: PacketWriter) -> None:
        w.int64(self.entity_unique_id)
        w.string(self.photo_name)
        w.string(self.item_name)

    @classmethod
    def read(cls, r: PacketReader) -> CreatePhoto:
        return cls(
            entity_unique_id=r.int64(),
            photo_name=r.string(),
            item_name=r.string(),
        )
