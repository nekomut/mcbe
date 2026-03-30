"""Packet: DimensionData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_DIMENSION_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class DimensionData(Packet):
    packet_id = ID_DIMENSION_DATA
    definitions: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.definitions)

    @classmethod
    def read(cls, r: PacketReader) -> DimensionData:
        return cls(
            definitions=r.byte_slice(),
        )
