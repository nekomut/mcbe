"""Packet: SetHud."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_HUD
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetHud(Packet):
    packet_id = ID_SET_HUD
    elements: bytes = b""
    visibility: int = 0

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.elements)
        w.varint32(self.visibility)

    @classmethod
    def read(cls, r: PacketReader) -> SetHud:
        return cls(
            elements=r.byte_slice(),
            visibility=r.varint32(),
        )
