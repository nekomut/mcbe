"""Packet: JigsawStructureData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_JIGSAW_STRUCTURE_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class JigsawStructureData(Packet):
    packet_id = ID_JIGSAW_STRUCTURE_DATA
    structure_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.bytes_raw(self.structure_data)

    @classmethod
    def read(cls, r: PacketReader) -> JigsawStructureData:
        return cls(
            structure_data=r.bytes_remaining(),
        )
