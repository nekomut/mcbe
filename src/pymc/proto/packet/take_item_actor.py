"""Packet: TakeItemActor."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_TAKE_ITEM_ACTOR
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class TakeItemActor(Packet):
    packet_id = ID_TAKE_ITEM_ACTOR
    item_entity_runtime_id: int = 0
    taker_entity_runtime_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.item_entity_runtime_id)
        w.varuint64(self.taker_entity_runtime_id)

    @classmethod
    def read(cls, r: PacketReader) -> TakeItemActor:
        return cls(
            item_entity_runtime_id=r.varuint64(),
            taker_entity_runtime_id=r.varuint64(),
        )
