"""Packet: MapInfoRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MAP_INFO_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MapInfoRequest(Packet):
    packet_id = ID_MAP_INFO_REQUEST
    map_id: int = 0
    client_pixels: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.map_id)
        w.byte_slice(self.client_pixels)

    @classmethod
    def read(cls, r: PacketReader) -> MapInfoRequest:
        return cls(
            map_id=r.varint64(),
            client_pixels=r.byte_slice(),
        )
