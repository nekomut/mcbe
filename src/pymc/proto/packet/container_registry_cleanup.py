"""Packet: ContainerRegistryCleanup."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CONTAINER_REGISTRY_CLEANUP
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ContainerRegistryCleanup(Packet):
    packet_id = ID_CONTAINER_REGISTRY_CLEANUP
    removed_containers: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.removed_containers)

    @classmethod
    def read(cls, r: PacketReader) -> ContainerRegistryCleanup:
        return cls(
            removed_containers=r.byte_slice(),
        )
