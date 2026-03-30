"""Packet: ServerSettingsRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_SETTINGS_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerSettingsRequest(Packet):
    packet_id = ID_SERVER_SETTINGS_REQUEST
    pass

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ServerSettingsRequest:
        return cls()
