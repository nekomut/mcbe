"""Packet: AgentAnimation."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_AGENT_ANIMATION
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AgentAnimation(Packet):
    packet_id = ID_AGENT_ANIMATION
    animation: int = 0
    entity_runtime_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.animation)
        w.varuint64(self.entity_runtime_id)

    @classmethod
    def read(cls, r: PacketReader) -> AgentAnimation:
        return cls(
            animation=r.uint8(),
            entity_runtime_id=r.varuint64(),
        )
