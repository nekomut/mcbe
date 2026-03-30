"""Packet: UpdateClientOptions."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_CLIENT_OPTIONS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdateClientOptions(Packet):
    packet_id = ID_UPDATE_CLIENT_OPTIONS
    graphics_mode: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.graphics_mode)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateClientOptions:
        return cls(
            graphics_mode=r.byte_slice(),
        )
