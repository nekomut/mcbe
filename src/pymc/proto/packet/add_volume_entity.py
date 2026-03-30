"""Packet: AddVolumeEntity."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADD_VOLUME_ENTITY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AddVolumeEntity(Packet):
    packet_id = ID_ADD_VOLUME_ENTITY
    entity_runtime_id: int = 0
    entity_metadata: dict = field(default_factory=dict)
    encoding_identifier: str = ""
    instance_identifier: str = ""
    bounds: bytes = b""
    dimension: int = 0
    engine_version: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varuint32(self.entity_runtime_id)
        w.nbt(self.entity_metadata)
        w.string(self.encoding_identifier)
        w.string(self.instance_identifier)
        w.byte_slice(self.bounds)
        w.varint32(self.dimension)
        w.string(self.engine_version)

    @classmethod
    def read(cls, r: PacketReader) -> AddVolumeEntity:
        return cls(
            entity_runtime_id=r.varuint32(),
            entity_metadata=r.nbt(),
            encoding_identifier=r.string(),
            instance_identifier=r.string(),
            bounds=r.byte_slice(),
            dimension=r.varint32(),
            engine_version=r.string(),
        )
