"""RequestNetworkSettings packet - client requests compression settings."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REQUEST_NETWORK_SETTINGS
from pymc.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class RequestNetworkSettings(Packet):
    packet_id = ID_REQUEST_NETWORK_SETTINGS
    client_protocol: int = 0

    def write(self, w: PacketWriter) -> None:
        w.be_int32(self.client_protocol)

    @classmethod
    def read(cls, r: PacketReader) -> RequestNetworkSettings:
        return cls(client_protocol=r.be_int32())
