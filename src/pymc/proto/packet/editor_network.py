"""Packet: EditorNetwork."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_EDITOR_NETWORK
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class EditorNetwork(Packet):
    packet_id = ID_EDITOR_NETWORK
    route_to_manager: bool = False
    payload: dict = field(default_factory=dict)

    def write(self, w: PacketWriter) -> None:
        w.bool(self.route_to_manager)
        w.nbt(self.payload)

    @classmethod
    def read(cls, r: PacketReader) -> EditorNetwork:
        return cls(
            route_to_manager=r.bool(),
            payload=r.nbt(),
        )
