"""Packet: DeathInfo."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_DEATH_INFO
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class DeathInfo(Packet):
    packet_id = ID_DEATH_INFO
    cause: str = ""
    messages: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.cause)
        w.byte_slice(self.messages)

    @classmethod
    def read(cls, r: PacketReader) -> DeathInfo:
        return cls(
            cause=r.string(),
            messages=r.byte_slice(),
        )
