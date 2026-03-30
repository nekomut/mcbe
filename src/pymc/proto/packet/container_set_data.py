"""Packet: ContainerSetData."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CONTAINER_SET_DATA
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ContainerSetData(Packet):
    packet_id = ID_CONTAINER_SET_DATA
    window_id: int = 0
    key: int = 0
    value: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.window_id)
        w.varint32(self.key)
        w.varint32(self.value)

    @classmethod
    def read(cls, r: PacketReader) -> ContainerSetData:
        return cls(
            window_id=r.uint8(),
            key=r.varint32(),
            value=r.varint32(),
        )
