"""Packet: RemoveObjective."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REMOVE_OBJECTIVE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class RemoveObjective(Packet):
    packet_id = ID_REMOVE_OBJECTIVE
    objective_name: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.objective_name)

    @classmethod
    def read(cls, r: PacketReader) -> RemoveObjective:
        return cls(
            objective_name=r.string(),
        )
