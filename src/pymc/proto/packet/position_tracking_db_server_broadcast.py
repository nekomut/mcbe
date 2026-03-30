"""Packet: PositionTrackingDBServerBroadcast."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_POSITION_TRACKING_DB_SERVER_BROADCAST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PositionTrackingDBServerBroadcast(Packet):
    packet_id = ID_POSITION_TRACKING_DB_SERVER_BROADCAST
    broadcast_action: int = 0
    tracking_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.broadcast_action)
        w.varint32(self.tracking_id)

    @classmethod
    def read(cls, r: PacketReader) -> PositionTrackingDBServerBroadcast:
        return cls(
            broadcast_action=r.uint8(),
            tracking_id=r.varint32(),
        )
