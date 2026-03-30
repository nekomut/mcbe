"""Packet: ResourcePackChunkRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_RESOURCE_PACK_CHUNK_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ResourcePackChunkRequest(Packet):
    packet_id = ID_RESOURCE_PACK_CHUNK_REQUEST
    uuid: str = ""
    chunk_index: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.uuid)
        w.uint32(self.chunk_index)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePackChunkRequest:
        return cls(
            uuid=r.string(),
            chunk_index=r.uint32(),
        )
