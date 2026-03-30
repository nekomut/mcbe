"""Packet: AutomationClientConnect."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_AUTOMATION_CLIENT_CONNECT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AutomationClientConnect(Packet):
    packet_id = ID_AUTOMATION_CLIENT_CONNECT
    server_uri: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.server_uri)

    @classmethod
    def read(cls, r: PacketReader) -> AutomationClientConnect:
        return cls(
            server_uri=r.string(),
        )
