"""Packet: ItemStackRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ITEM_STACK_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ItemStackRequest(Packet):
    packet_id = ID_ITEM_STACK_REQUEST
    requests: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.requests)

    @classmethod
    def read(cls, r: PacketReader) -> ItemStackRequest:
        return cls(
            requests=r.byte_slice(),
        )
