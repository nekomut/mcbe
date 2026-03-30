"""Packet: PlayerSkin."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_SKIN
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PlayerSkin(Packet):
    packet_id = ID_PLAYER_SKIN
    uuid: UUID = 0
    skin: bytes = b""
    new_skin_name: str = ""
    old_skin_name: str = ""

    def write(self, w: PacketWriter) -> None:
        w.uuid(self.uuid)
        w.byte_slice(self.skin)
        w.string(self.new_skin_name)
        w.string(self.old_skin_name)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerSkin:
        return cls(
            uuid=r.uuid(),
            skin=r.byte_slice(),
            new_skin_name=r.string(),
            old_skin_name=r.string(),
        )
