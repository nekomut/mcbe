"""Packet: EmoteList."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_EMOTE_LIST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class EmoteList(Packet):
    packet_id = ID_EMOTE_LIST
    player_runtime_id: int = 0
    emote_pieces: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.player_runtime_id)
        w.byte_slice(self.emote_pieces)

    @classmethod
    def read(cls, r: PacketReader) -> EmoteList:
        return cls(
            player_runtime_id=r.varuint64(),
            emote_pieces=r.byte_slice(),
        )
