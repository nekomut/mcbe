"""Packet: AvailableCommands."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_AVAILABLE_COMMANDS
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AvailableCommands(Packet):
    packet_id = ID_AVAILABLE_COMMANDS
    enum_values: bytes = b""
    chained_subcommand_values: bytes = b""
    suffixes: bytes = b""
    enums: bytes = b""
    chained_subcommands: bytes = b""
    commands: bytes = b""
    dynamic_enums: bytes = b""
    constraints: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.enum_values)
        w.byte_slice(self.chained_subcommand_values)
        w.byte_slice(self.suffixes)
        w.byte_slice(self.enums)
        w.byte_slice(self.chained_subcommands)
        w.byte_slice(self.commands)
        w.byte_slice(self.dynamic_enums)
        w.byte_slice(self.constraints)

    @classmethod
    def read(cls, r: PacketReader) -> AvailableCommands:
        return cls(
            enum_values=r.byte_slice(),
            chained_subcommand_values=r.byte_slice(),
            suffixes=r.byte_slice(),
            enums=r.byte_slice(),
            chained_subcommands=r.byte_slice(),
            commands=r.byte_slice(),
            dynamic_enums=r.byte_slice(),
            constraints=r.byte_slice(),
        )
