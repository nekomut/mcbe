"""Packet: SubClientLogin."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SUB_CLIENT_LOGIN
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SubClientLogin(Packet):
    packet_id = ID_SUB_CLIENT_LOGIN
    connection_request: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.connection_request)

    @classmethod
    def read(cls, r: PacketReader) -> SubClientLogin:
        return cls(
            connection_request=r.byte_slice(),
        )
