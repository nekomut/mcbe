"""Login packet - client sends authentication data."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_LOGIN
from pymc.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class Login(Packet):
    packet_id = ID_LOGIN
    client_protocol: int = 0
    connection_request: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.be_int32(self.client_protocol)
        w.byte_slice(self.connection_request)

    @classmethod
    def read(cls, r: PacketReader) -> Login:
        return cls(
            client_protocol=r.be_int32(),
            connection_request=r.byte_slice(),
        )
