"""Packet: ClientBoundTextureShift."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_TEXTURE_SHIFT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ClientBoundTextureShift(Packet):
    packet_id = ID_CLIENT_BOUND_TEXTURE_SHIFT
    action_id: int = 0
    collection_name: str = ""
    from_step: str = ""
    to_step: str = ""
    all_steps: bytes = b""
    current_length_ticks: int = 0
    total_length_ticks: int = 0
    enabled: bool = False

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_id)
        w.string(self.collection_name)
        w.string(self.from_step)
        w.string(self.to_step)
        w.byte_slice(self.all_steps)
        w.varuint64(self.current_length_ticks)
        w.varuint64(self.total_length_ticks)
        w.bool(self.enabled)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundTextureShift:
        return cls(
            action_id=r.uint8(),
            collection_name=r.string(),
            from_step=r.string(),
            to_step=r.string(),
            all_steps=r.byte_slice(),
            current_length_ticks=r.varuint64(),
            total_length_ticks=r.varuint64(),
            enabled=r.bool(),
        )
