"""Packet: Interact."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_INTERACT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class Interact(Packet):
    packet_id = ID_INTERACT
    action_type: int = 0
    target_entity_runtime_id: int = 0
    position: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_type)
        w.varuint64(self.target_entity_runtime_id)
        w.byte_slice(self.position)

    @classmethod
    def read(cls, r: PacketReader) -> Interact:
        return cls(
            action_type=r.uint8(),
            target_entity_runtime_id=r.varuint64(),
            position=r.byte_slice(),
        )
