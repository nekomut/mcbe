"""Packet: UpdateAttributes."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_UPDATE_ATTRIBUTES
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class UpdateAttributes(Packet):
    packet_id = ID_UPDATE_ATTRIBUTES
    entity_runtime_id: int = 0
    attributes: bytes = b""
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.byte_slice(self.attributes)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> UpdateAttributes:
        return cls(
            entity_runtime_id=r.varuint64(),
            attributes=r.byte_slice(),
            tick=r.varuint64(),
        )
