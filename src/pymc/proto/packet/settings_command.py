"""Packet: SettingsCommand."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SETTINGS_COMMAND
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class SettingsCommand(Packet):
    packet_id = ID_SETTINGS_COMMAND
    command_line: str = ""
    suppress_output: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.command_line)
        w.bool(self.suppress_output)

    @classmethod
    def read(cls, r: PacketReader) -> SettingsCommand:
        return cls(
            command_line=r.string(),
            suppress_output=r.bool(),
        )
