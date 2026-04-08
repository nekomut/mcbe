"""Packet: AddVolumeEntity."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_ADD_VOLUME_ENTITY
from mcbe.proto.pool import Packet, register_server_packet
from mcbe.proto.types import BlockPos


@register_server_packet
@dataclass
class AddVolumeEntity(Packet):
    packet_id = ID_ADD_VOLUME_ENTITY
    entity_runtime_id: int = 0
    entity_metadata: dict = field(default_factory=dict)
    encoding_identifier: str = ""
    instance_identifier: str = ""
    min_bounds: BlockPos = field(default_factory=BlockPos)
    max_bounds: BlockPos = field(default_factory=BlockPos)
    dimension: int = 0
    engine_version: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.entity_runtime_id)
        w.nbt(self.entity_metadata)
        w.string(self.encoding_identifier)
        w.string(self.instance_identifier)
        w.block_pos(self.min_bounds)
        w.block_pos(self.max_bounds)
        w.varint32(self.dimension)
        w.string(self.engine_version)

    @classmethod
    def read(cls, r: PacketReader) -> AddVolumeEntity:
        return cls(
            entity_runtime_id=r.varuint32(),
            entity_metadata=r.nbt(),
            encoding_identifier=r.string(),
            instance_identifier=r.string(),
            min_bounds=r.block_pos(),
            max_bounds=r.block_pos(),
            dimension=r.varint32(),
            engine_version=r.string(),
        )
