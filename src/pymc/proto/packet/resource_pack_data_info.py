"""Packet: ResourcePackDataInfo."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_RESOURCE_PACK_DATA_INFO
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ResourcePackDataInfo(Packet):
    packet_id = ID_RESOURCE_PACK_DATA_INFO
    uuid: str = ""
    data_chunk_size: int = 0
    chunk_count: int = 0
    size: int = 0
    hash: bytes = b""
    premium: bool = False
    pack_type: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.uuid)
        w.uint32(self.data_chunk_size)
        w.uint32(self.chunk_count)
        w.uint64(self.size)
        w.byte_slice(self.hash)
        w.bool(self.premium)
        w.uint8(self.pack_type)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePackDataInfo:
        return cls(
            uuid=r.string(),
            data_chunk_size=r.uint32(),
            chunk_count=r.uint32(),
            size=r.uint64(),
            hash=r.byte_slice(),
            premium=r.bool(),
            pack_type=r.uint8(),
        )
