"""Packet: SetCommandsEnabled."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_COMMANDS_ENABLED
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SetCommandsEnabled(Packet):
    packet_id = ID_SET_COMMANDS_ENABLED
    enabled: bool = False

    def write(self, w: PacketWriter) -> None:
        w.bool(self.enabled)

    @classmethod
    def read(cls, r: PacketReader) -> SetCommandsEnabled:
        return cls(
            enabled=r.bool(),
        )
