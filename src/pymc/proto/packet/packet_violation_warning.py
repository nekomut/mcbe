"""Packet: PacketViolationWarning."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PACKET_VIOLATION_WARNING
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PacketViolationWarning(Packet):
    packet_id = ID_PACKET_VIOLATION_WARNING
    type: int = 0
    severity: int = 0
    packet_id: int = 0
    violation_context: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.type)
        w.varint32(self.severity)
        w.varint32(self.packet_id)
        w.string(self.violation_context)

    @classmethod
    def read(cls, r: PacketReader) -> PacketViolationWarning:
        return cls(
            type=r.varint32(),
            severity=r.varint32(),
            packet_id=r.varint32(),
            violation_context=r.string(),
        )
