"""Packet: ResourcePacksReadyForValidation."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_RESOURCE_PACKS_READY_FOR_VALIDATION
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ResourcePacksReadyForValidation(Packet):
    packet_id = ID_RESOURCE_PACKS_READY_FOR_VALIDATION
    pass

    def write(self, w: PacketWriter) -> None:
        pass

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePacksReadyForValidation:
        return cls()
