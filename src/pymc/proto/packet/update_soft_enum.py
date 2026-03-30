"""Packet: UpdateSoftEnum."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_SOFT_ENUM
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdateSoftEnum(Packet):
    packet_id = ID_UPDATE_SOFT_ENUM
    enum_type: str = ""
    options: bytes = b""
    action_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.enum_type)
        w.byte_slice(self.options)
        w.uint8(self.action_type)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateSoftEnum:
        return cls(
            enum_type=r.string(),
            options=r.byte_slice(),
            action_type=r.uint8(),
        )
