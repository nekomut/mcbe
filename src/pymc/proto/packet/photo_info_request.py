"""Packet: PhotoInfoRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PHOTO_INFO_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PhotoInfoRequest(Packet):
    packet_id = ID_PHOTO_INFO_REQUEST
    photo_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.photo_id)

    @classmethod
    def read(cls, r: PacketReader) -> PhotoInfoRequest:
        return cls(
            photo_id=r.varint64(),
        )
