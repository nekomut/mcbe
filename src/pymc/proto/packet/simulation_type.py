"""Packet: SimulationType."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SIMULATION_TYPE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SimulationType(Packet):
    packet_id = ID_SIMULATION_TYPE
    simulation_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.simulation_type)

    @classmethod
    def read(cls, r: PacketReader) -> SimulationType:
        return cls(
            simulation_type=r.uint8(),
        )
