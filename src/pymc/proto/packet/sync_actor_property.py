"""Packet: SyncActorProperty."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SYNC_ACTOR_PROPERTY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SyncActorProperty(Packet):
    packet_id = ID_SYNC_ACTOR_PROPERTY
    property_data: dict = field(default_factory=dict)

    def write(self, w: PacketWriter) -> None:
        w.nbt(self.property_data)

    @classmethod
    def read(cls, r: PacketReader) -> SyncActorProperty:
        return cls(
            property_data=r.nbt(),
        )
