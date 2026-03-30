"""Packet: CreativeContent."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CREATIVE_CONTENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CreativeContent(Packet):
    packet_id = ID_CREATIVE_CONTENT
    groups: bytes = b""
    items: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.groups)
        w.byte_slice(self.items)

    @classmethod
    def read(cls, r: PacketReader) -> CreativeContent:
        return cls(
            groups=r.byte_slice(),
            items=r.byte_slice(),
        )
