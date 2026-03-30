"""Packet: SetDisplayObjective."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_DISPLAY_OBJECTIVE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetDisplayObjective(Packet):
    packet_id = ID_SET_DISPLAY_OBJECTIVE
    display_slot: str = ""
    objective_name: str = ""
    display_name: str = ""
    criteria_name: str = ""
    sort_order: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.display_slot)
        w.string(self.objective_name)
        w.string(self.display_name)
        w.string(self.criteria_name)
        w.varint32(self.sort_order)

    @classmethod
    def read(cls, r: PacketReader) -> SetDisplayObjective:
        return cls(
            display_slot=r.string(),
            objective_name=r.string(),
            display_name=r.string(),
            criteria_name=r.string(),
            sort_order=r.varint32(),
        )
