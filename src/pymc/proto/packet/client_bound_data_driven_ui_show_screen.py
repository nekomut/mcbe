"""Packet: ClientBoundDataDrivenUIShowScreen."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_DATA_DRIVEN_UI_SHOW_SCREEN
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundDataDrivenUIShowScreen(Packet):
    packet_id = ID_CLIENT_BOUND_DATA_DRIVEN_UI_SHOW_SCREEN
    screen_id: str = ""
    form_id: int = 0
    data_instance_id: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.screen_id)
        w.uint32(self.form_id)
        w.byte_slice(self.data_instance_id)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundDataDrivenUIShowScreen:
        return cls(
            screen_id=r.string(),
            form_id=r.uint32(),
            data_instance_id=r.byte_slice(),
        )
