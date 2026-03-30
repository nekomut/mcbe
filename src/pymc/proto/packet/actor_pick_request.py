"""Packet: ActorPickRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ACTOR_PICK_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ActorPickRequest(Packet):
    packet_id = ID_ACTOR_PICK_REQUEST
    entity_unique_id: int = 0
    hot_bar_slot: int = 0
    with_data: bool = False

    def write(self, w: PacketWriter) -> None:
        w.int64(self.entity_unique_id)
        w.uint8(self.hot_bar_slot)
        w.bool(self.with_data)

    @classmethod
    def read(cls, r: PacketReader) -> ActorPickRequest:
        return cls(
            entity_unique_id=r.int64(),
            hot_bar_slot=r.uint8(),
            with_data=r.bool(),
        )
