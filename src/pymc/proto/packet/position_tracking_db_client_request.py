"""Packet: PositionTrackingDBClientRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_POSITION_TRACKING_DB_CLIENT_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PositionTrackingDBClientRequest(Packet):
    packet_id = ID_POSITION_TRACKING_DB_CLIENT_REQUEST
    request_action: int = 0
    tracking_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.request_action)
        w.varint32(self.tracking_id)

    @classmethod
    def read(cls, r: PacketReader) -> PositionTrackingDBClientRequest:
        return cls(
            request_action=r.uint8(),
            tracking_id=r.varint32(),
        )
