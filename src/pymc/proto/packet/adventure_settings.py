"""Packet: AdventureSettings."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADVENTURE_SETTINGS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AdventureSettings(Packet):
    packet_id = ID_ADVENTURE_SETTINGS
    flags: int = 0
    command_permission_level: int = 0
    action_permissions: int = 0
    permission_level: int = 0
    custom_stored_permissions: int = 0
    player_unique_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.flags)
        w.varuint32(self.command_permission_level)
        w.varuint32(self.action_permissions)
        w.varuint32(self.permission_level)
        w.varuint32(self.custom_stored_permissions)
        w.int64(self.player_unique_id)

    @classmethod
    def read(cls, r: PacketReader) -> AdventureSettings:
        return cls(
            flags=r.varuint32(),
            command_permission_level=r.varuint32(),
            action_permissions=r.varuint32(),
            permission_level=r.varuint32(),
            custom_stored_permissions=r.varuint32(),
            player_unique_id=r.int64(),
        )
