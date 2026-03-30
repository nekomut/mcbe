"""Packet: ResourcePackChunkData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_RESOURCE_PACK_CHUNK_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ResourcePackChunkData(Packet):
    packet_id = ID_RESOURCE_PACK_CHUNK_DATA
    uuid: str = ""
    chunk_index: int = 0
    data_offset: int = 0
    data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.uuid)
        w.uint32(self.chunk_index)
        w.uint64(self.data_offset)
        w.byte_slice(self.data)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePackChunkData:
        return cls(
            uuid=r.string(),
            chunk_index=r.uint32(),
            data_offset=r.uint64(),
            data=r.byte_slice(),
        )
