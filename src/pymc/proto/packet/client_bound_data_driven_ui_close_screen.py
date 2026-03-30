"""Packet: ClientBoundDataDrivenUICloseScreen."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_DATA_DRIVEN_UI_CLOSE_SCREEN
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundDataDrivenUICloseScreen(Packet):
    packet_id = ID_CLIENT_BOUND_DATA_DRIVEN_UI_CLOSE_SCREEN
    form_id: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.form_id)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundDataDrivenUICloseScreen:
        return cls(
            form_id=r.byte_slice(),
        )
