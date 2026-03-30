"""SetLocalPlayerAsInitialised packet - client signals readiness."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_LOCAL_PLAYER_AS_INITIALISED
from pymc.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class SetLocalPlayerAsInitialised(Packet):
    packet_id = ID_SET_LOCAL_PLAYER_AS_INITIALISED
    entity_runtime_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)

    @classmethod
    def read(cls, r: PacketReader) -> SetLocalPlayerAsInitialised:
        return cls(entity_runtime_id=r.varuint64())
