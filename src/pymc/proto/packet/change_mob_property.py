"""Packet: ChangeMobProperty."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CHANGE_MOB_PROPERTY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ChangeMobProperty(Packet):
    packet_id = ID_CHANGE_MOB_PROPERTY
    entity_unique_id: int = 0
    property: str = ""
    bool_value: bool = False
    string_value: str = ""
    int_value: int = 0
    float_value: float = 0.0

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)
        w.string(self.property)
        w.bool(self.bool_value)
        w.string(self.string_value)
        w.varint32(self.int_value)
        w.float32(self.float_value)

    @classmethod
    def read(cls, r: PacketReader) -> ChangeMobProperty:
        return cls(
            entity_unique_id=r.varint64(),
            property=r.string(),
            bool_value=r.bool(),
            string_value=r.string(),
            int_value=r.varint32(),
            float_value=r.float32(),
        )
