"""Packet: AgentAction."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_AGENT_ACTION
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AgentAction(Packet):
    packet_id = ID_AGENT_ACTION
    identifier: str = ""
    action: int = 0
    response: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.identifier)
        w.int32(self.action)
        w.byte_slice(self.response)

    @classmethod
    def read(cls, r: PacketReader) -> AgentAction:
        return cls(
            identifier=r.string(),
            action=r.int32(),
            response=r.byte_slice(),
        )
