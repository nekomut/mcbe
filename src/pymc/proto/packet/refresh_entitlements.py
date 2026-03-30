"""Packet: RefreshEntitlements."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REFRESH_ENTITLEMENTS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class RefreshEntitlements(Packet):
    packet_id = ID_REFRESH_ENTITLEMENTS
    pass

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> RefreshEntitlements:
        return cls()
