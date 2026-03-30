"""Packet: ServerBoundDataStore."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_BOUND_DATA_STORE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerBoundDataStore(Packet):
    packet_id = ID_SERVER_BOUND_DATA_STORE
    update: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.update)

    @classmethod
    def read(cls, r: PacketReader) -> ServerBoundDataStore:
        return cls(
            update=r.byte_slice(),
        )
