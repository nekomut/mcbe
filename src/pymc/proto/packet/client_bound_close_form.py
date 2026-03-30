"""Packet: ClientBoundCloseForm."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_CLOSE_FORM
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundCloseForm(Packet):
    packet_id = ID_CLIENT_BOUND_CLOSE_FORM
    pass

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundCloseForm:
        return cls()
