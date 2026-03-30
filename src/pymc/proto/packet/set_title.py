"""Packet: SetTitle."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_TITLE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetTitle(Packet):
    packet_id = ID_SET_TITLE
    action_type: int = 0
    text: str = ""
    fade_in_duration: int = 0
    remain_duration: int = 0
    fade_out_duration: int = 0
    xuid: str = ""
    platform_online_id: str = ""
    filtered_message: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.action_type)
        w.string(self.text)
        w.varint32(self.fade_in_duration)
        w.varint32(self.remain_duration)
        w.varint32(self.fade_out_duration)
        w.string(self.xuid)
        w.string(self.platform_online_id)
        w.string(self.filtered_message)

    @classmethod
    def read(cls, r: PacketReader) -> SetTitle:
        return cls(
            action_type=r.varint32(),
            text=r.string(),
            fade_in_duration=r.varint32(),
            remain_duration=r.varint32(),
            fade_out_duration=r.varint32(),
            xuid=r.string(),
            platform_online_id=r.string(),
            filtered_message=r.string(),
        )
