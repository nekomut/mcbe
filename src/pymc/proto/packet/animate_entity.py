"""Packet: AnimateEntity."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ANIMATE_ENTITY
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AnimateEntity(Packet):
    packet_id = ID_ANIMATE_ENTITY
    animation: str = ""
    next_state: str = ""
    stop_condition: str = ""
    stop_condition_version: int = 0
    controller: str = ""
    blend_out_time: float = 0.0
    entity_runtime_i_ds: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.animation)
        w.string(self.next_state)
        w.string(self.stop_condition)
        w.int32(self.stop_condition_version)
        w.string(self.controller)
        w.float32(self.blend_out_time)
        w.byte_slice(self.entity_runtime_i_ds)

    @classmethod
    def read(cls, r: PacketReader) -> AnimateEntity:
        return cls(
            animation=r.string(),
            next_state=r.string(),
            stop_condition=r.string(),
            stop_condition_version=r.int32(),
            controller=r.string(),
            blend_out_time=r.float32(),
            entity_runtime_i_ds=r.byte_slice(),
        )
