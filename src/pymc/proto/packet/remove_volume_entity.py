"""Packet: RemoveVolumeEntity."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REMOVE_VOLUME_ENTITY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class RemoveVolumeEntity(Packet):
    packet_id = ID_REMOVE_VOLUME_ENTITY
    entity_runtime_id: int = 0
    dimension: int = 0

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.entity_runtime_id)
        w.varint32(self.dimension)

    @classmethod
    def read(cls, r: PacketReader) -> RemoveVolumeEntity:
        return cls(
            entity_runtime_id=r.varuint32(),
            dimension=r.varint32(),
        )
