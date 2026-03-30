"""Packet: TrimData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_TRIM_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class TrimData(Packet):
    packet_id = ID_TRIM_DATA
    patterns: bytes = b""
    materials: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.patterns)
        w.byte_slice(self.materials)

    @classmethod
    def read(cls, r: PacketReader) -> TrimData:
        return cls(
            patterns=r.byte_slice(),
            materials=r.byte_slice(),
        )
