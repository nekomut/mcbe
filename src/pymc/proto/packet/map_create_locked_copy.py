"""Packet: MapCreateLockedCopy."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_MAP_CREATE_LOCKED_COPY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class MapCreateLockedCopy(Packet):
    packet_id = ID_MAP_CREATE_LOCKED_COPY
    original_map_id: int = 0
    new_map_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.original_map_id)
        w.varint64(self.new_map_id)

    @classmethod
    def read(cls, r: PacketReader) -> MapCreateLockedCopy:
        return cls(
            original_map_id=r.varint64(),
            new_map_id=r.varint64(),
        )
