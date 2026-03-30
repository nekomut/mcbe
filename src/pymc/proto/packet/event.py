"""Packet: Event."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_EVENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class Event(Packet):
    packet_id = ID_EVENT
    entity_runtime_id: int = 0
    use_player_id: bool = False
    event: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_runtime_id)
        w.bool(self.use_player_id)
        w.byte_slice(self.event)

    @classmethod
    def read(cls, r: PacketReader) -> Event:
        return cls(
            entity_runtime_id=r.varint64(),
            use_player_id=r.bool(),
            event=r.byte_slice(),
        )
