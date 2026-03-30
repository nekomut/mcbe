"""Packet: ServerBoundDataDrivenScreenClosed."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SERVER_BOUND_DATA_DRIVEN_SCREEN_CLOSED
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ServerBoundDataDrivenScreenClosed(Packet):
    packet_id = ID_SERVER_BOUND_DATA_DRIVEN_SCREEN_CLOSED
    form_id: bytes = b""
    close_reason: int = 0

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.form_id)
        w.uint8(self.close_reason)

    @classmethod
    def read(cls, r: PacketReader) -> ServerBoundDataDrivenScreenClosed:
        return cls(
            form_id=r.byte_slice(),
            close_reason=r.uint8(),
        )
