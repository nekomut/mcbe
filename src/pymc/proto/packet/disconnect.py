"""Disconnect packet."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_DISCONNECT
from pymc.proto.pool import Packet, register_bidirectional


@register_bidirectional
@dataclass
class Disconnect(Packet):
    packet_id = ID_DISCONNECT
    reason: int = 0
    hide_disconnection_screen: bool = False
    message: str = ""
    filtered_message: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varint32(self.reason)
        w.bool(self.hide_disconnection_screen)
        if not self.hide_disconnection_screen:
            w.string(self.message)
            w.string(self.filtered_message)

    @classmethod
    def read(cls, r: PacketReader) -> Disconnect:
        reason = r.varint32()
        hide = r.bool()
        message = ""
        filtered = ""
        if not hide:
            message = r.string()
            filtered = r.string()
        return cls(
            reason=reason,
            hide_disconnection_screen=hide,
            message=message,
            filtered_message=filtered,
        )
