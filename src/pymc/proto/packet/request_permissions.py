"""Packet: RequestPermissions."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_REQUEST_PERMISSIONS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class RequestPermissions(Packet):
    packet_id = ID_REQUEST_PERMISSIONS
    entity_unique_id: int = 0
    permission_level: int = 0
    requested_permissions: int = 0

    def write(self, w: PacketWriter) -> None:
        w.int64(self.entity_unique_id)
        w.varint32(self.permission_level)
        w.uint16(self.requested_permissions)

    @classmethod
    def read(cls, r: PacketReader) -> RequestPermissions:
        return cls(
            entity_unique_id=r.int64(),
            permission_level=r.varint32(),
            requested_permissions=r.uint16(),
        )
