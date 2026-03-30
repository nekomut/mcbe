"""Packet: ServerSettingsResponse."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_SETTINGS_RESPONSE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerSettingsResponse(Packet):
    packet_id = ID_SERVER_SETTINGS_RESPONSE
    form_id: int = 0
    form_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.form_id)
        w.byte_slice(self.form_data)

    @classmethod
    def read(cls, r: PacketReader) -> ServerSettingsResponse:
        return cls(
            form_id=r.varuint32(),
            form_data=r.byte_slice(),
        )
