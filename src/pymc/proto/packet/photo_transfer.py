"""Packet: PhotoTransfer."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PHOTO_TRANSFER
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PhotoTransfer(Packet):
    packet_id = ID_PHOTO_TRANSFER
    photo_name: str = ""
    photo_data: bytes = b""
    book_id: str = ""
    photo_type: int = 0
    source_type: int = 0
    owner_entity_unique_id: int = 0
    new_photo_name: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.photo_name)
        w.byte_slice(self.photo_data)
        w.string(self.book_id)
        w.uint8(self.photo_type)
        w.uint8(self.source_type)
        w.int64(self.owner_entity_unique_id)
        w.string(self.new_photo_name)

    @classmethod
    def read(cls, r: PacketReader) -> PhotoTransfer:
        return cls(
            photo_name=r.string(),
            photo_data=r.byte_slice(),
            book_id=r.string(),
            photo_type=r.uint8(),
            source_type=r.uint8(),
            owner_entity_unique_id=r.int64(),
            new_photo_name=r.string(),
        )
