"""Packet: ServerBoundPackSettingChange."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_BOUND_PACK_SETTING_CHANGE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerBoundPackSettingChange(Packet):
    packet_id = ID_SERVER_BOUND_PACK_SETTING_CHANGE
    pack_id: UUID = 0
    pack_setting: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uuid(self.pack_id)
        w.byte_slice(self.pack_setting)

    @classmethod
    def read(cls, r: PacketReader) -> ServerBoundPackSettingChange:
        return cls(
            pack_id=r.uuid(),
            pack_setting=r.byte_slice(),
        )
