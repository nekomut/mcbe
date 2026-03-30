"""Packet: Transfer."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_TRANSFER
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class Transfer(Packet):
    packet_id = ID_TRANSFER
    address: str = ""
    port: int = 0
    reload_world: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.address)
        w.uint16(self.port)
        w.bool(self.reload_world)

    @classmethod
    def read(cls, r: PacketReader) -> Transfer:
        return cls(
            address=r.string(),
            port=r.uint16(),
            reload_world=r.bool(),
        )
