"""Packet: EducationResourceURI."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_EDUCATION_RESOURCE_URI
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class EducationResourceURI(Packet):
    packet_id = ID_EDUCATION_RESOURCE_URI
    resource: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.resource)

    @classmethod
    def read(cls, r: PacketReader) -> EducationResourceURI:
        return cls(
            resource=r.byte_slice(),
        )
