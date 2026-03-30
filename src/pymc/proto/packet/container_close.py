"""Packet: ContainerClose."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CONTAINER_CLOSE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ContainerClose(Packet):
    packet_id = ID_CONTAINER_CLOSE
    window_id: int = 0
    container_type: int = 0
    server_side: bool = False

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.window_id)
        w.uint8(self.container_type)
        w.bool(self.server_side)

    @classmethod
    def read(cls, r: PacketReader) -> ContainerClose:
        return cls(
            window_id=r.uint8(),
            container_type=r.uint8(),
            server_side=r.bool(),
        )
