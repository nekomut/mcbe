"""Packet: UpdateAdventureSettings."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_ADVENTURE_SETTINGS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdateAdventureSettings(Packet):
    packet_id = ID_UPDATE_ADVENTURE_SETTINGS
    no_pv_m: bool = False
    no_mv_p: bool = False
    immutable_world: bool = False
    show_name_tags: bool = False
    auto_jump: bool = False

    def write(self, w: PacketWriter) -> None:
        w.bool(self.no_pv_m)
        w.bool(self.no_mv_p)
        w.bool(self.immutable_world)
        w.bool(self.show_name_tags)
        w.bool(self.auto_jump)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateAdventureSettings:
        return cls(
            no_pv_m=r.bool(),
            no_mv_p=r.bool(),
            immutable_world=r.bool(),
            show_name_tags=r.bool(),
            auto_jump=r.bool(),
        )
