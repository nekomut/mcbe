"""Packet: ItemStackResponse."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ITEM_STACK_RESPONSE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ItemStackResponse(Packet):
    packet_id = ID_ITEM_STACK_RESPONSE
    responses: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.responses)

    @classmethod
    def read(cls, r: PacketReader) -> ItemStackResponse:
        return cls(
            responses=r.byte_slice(),
        )
