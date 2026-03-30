"""Handshake packets for encryption setup."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_TO_SERVER_HANDSHAKE, ID_SERVER_TO_CLIENT_HANDSHAKE
from pymc.proto.pool import Packet, register_bidirectional, register_server_packet


@register_server_packet
@dataclass
class ServerToClientHandshake(Packet):
    packet_id = ID_SERVER_TO_CLIENT_HANDSHAKE
    jwt: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.jwt)

    @classmethod
    def read(cls, r: PacketReader) -> ServerToClientHandshake:
        return cls(jwt=r.byte_slice())


@register_bidirectional
@dataclass
class ClientToServerHandshake(Packet):
    packet_id = ID_CLIENT_TO_SERVER_HANDSHAKE

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ClientToServerHandshake:
        return cls()
