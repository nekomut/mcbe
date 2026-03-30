"""Packet: BiomeDefinitionList."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_BIOME_DEFINITION_LIST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class BiomeDefinitionList(Packet):
    packet_id = ID_BIOME_DEFINITION_LIST
    biome_definitions: bytes = b""
    string_list: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.biome_definitions)
        w.byte_slice(self.string_list)

    @classmethod
    def read(cls, r: PacketReader) -> BiomeDefinitionList:
        return cls(
            biome_definitions=r.byte_slice(),
            string_list=r.byte_slice(),
        )
