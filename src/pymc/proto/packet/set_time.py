"""Packet: SetTime."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_TIME
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetTime(Packet):
    packet_id = ID_SET_TIME
    time: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.time)

    @classmethod
    def read(cls, r: PacketReader) -> SetTime:
        return cls(
            time=r.varint32(),
        )
