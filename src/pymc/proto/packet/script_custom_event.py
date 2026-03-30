"""Packet: ScriptCustomEvent."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SCRIPT_CUSTOM_EVENT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ScriptCustomEvent(Packet):
    packet_id = ID_SCRIPT_CUSTOM_EVENT
    event_name: str = ""
    event_data: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.string(self.event_name)
        w.byte_slice(self.event_data)

    @classmethod
    def read(cls, r: PacketReader) -> ScriptCustomEvent:
        return cls(
            event_name=r.string(),
            event_data=r.byte_slice(),
        )
