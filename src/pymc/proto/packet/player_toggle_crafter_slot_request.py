"""Packet: PlayerToggleCrafterSlotRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_TOGGLE_CRAFTER_SLOT_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class PlayerToggleCrafterSlotRequest(Packet):
    packet_id = ID_PLAYER_TOGGLE_CRAFTER_SLOT_REQUEST
    pos_x: int = 0
    pos_y: int = 0
    pos_z: int = 0
    slot: int = 0
    disabled: bool = False

    def write(self, w: PacketWriter) -> None:
        w.int32(self.pos_x)
        w.int32(self.pos_y)
        w.int32(self.pos_z)
        w.uint8(self.slot)
        w.bool(self.disabled)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerToggleCrafterSlotRequest:
        return cls(
            pos_x=r.int32(),
            pos_y=r.int32(),
            pos_z=r.int32(),
            slot=r.uint8(),
            disabled=r.bool(),
        )
