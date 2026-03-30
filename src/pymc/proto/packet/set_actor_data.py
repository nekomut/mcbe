"""Packet: SetActorData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_ACTOR_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetActorData(Packet):
    packet_id = ID_SET_ACTOR_DATA
    entity_runtime_id: int = 0
    entity_metadata: bytes = b""
    entity_properties: bytes = b""
    tick: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.byte_slice(self.entity_metadata)
        w.byte_slice(self.entity_properties)
        w.varuint64(self.tick)

    @classmethod
    def read(cls, r: PacketReader) -> SetActorData:
        return cls(
            entity_runtime_id=r.varuint64(),
            entity_metadata=r.byte_slice(),
            entity_properties=r.byte_slice(),
            tick=r.varuint64(),
        )
