"""Packet: NetworkChunkPublisherUpdate."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_NETWORK_CHUNK_PUBLISHER_UPDATE
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import BlockPos


@register_server_packet
@dataclass
class NetworkChunkPublisherUpdate(Packet):
    packet_id = ID_NETWORK_CHUNK_PUBLISHER_UPDATE
    position: BlockPos = 0
    radius: int = 0
    saved_chunks: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.block_pos(self.position)
        w.varuint32(self.radius)
        w.byte_slice(self.saved_chunks)

    @classmethod
    def read(cls, r: PacketReader) -> NetworkChunkPublisherUpdate:
        return cls(
            position=r.block_pos(),
            radius=r.varuint32(),
            saved_chunks=r.byte_slice(),
        )
