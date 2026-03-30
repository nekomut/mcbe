"""Packet: Emote."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_EMOTE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class Emote(Packet):
    packet_id = ID_EMOTE
    entity_runtime_id: int = 0
    emote_length: int = 0
    emote_id: str = ""
    xuid: str = ""
    platform_id: str = ""
    flags: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.varuint32(self.emote_length)
        w.string(self.emote_id)
        w.string(self.xuid)
        w.string(self.platform_id)
        w.uint8(self.flags)

    @classmethod
    def read(cls, r: PacketReader) -> Emote:
        return cls(
            entity_runtime_id=r.varuint64(),
            emote_length=r.varuint32(),
            emote_id=r.string(),
            xuid=r.string(),
            platform_id=r.string(),
            flags=r.uint8(),
        )
