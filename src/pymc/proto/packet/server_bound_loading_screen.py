"""Packet: ServerBoundLoadingScreen."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_BOUND_LOADING_SCREEN
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerBoundLoadingScreen(Packet):
    packet_id = ID_SERVER_BOUND_LOADING_SCREEN
    type: int = 0
    loading_screen_id: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.type)
        w.byte_slice(self.loading_screen_id)

    @classmethod
    def read(cls, r: PacketReader) -> ServerBoundLoadingScreen:
        return cls(
            type=r.varint32(),
            loading_screen_id=r.byte_slice(),
        )
