"""Packet: CurrentStructureFeature."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CURRENT_STRUCTURE_FEATURE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CurrentStructureFeature(Packet):
    packet_id = ID_CURRENT_STRUCTURE_FEATURE
    current_feature: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.current_feature)

    @classmethod
    def read(cls, r: PacketReader) -> CurrentStructureFeature:
        return cls(
            current_feature=r.string(),
        )
