"""Packet: CommandRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_COMMAND_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CommandRequest(Packet):
    packet_id = ID_COMMAND_REQUEST
    command_line: str = ""
    command_origin: bytes = b""
    internal: bool = False
    version: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.command_line)
        w.byte_slice(self.command_origin)
        w.bool(self.internal)
        w.string(self.version)

    @classmethod
    def read(cls, r: PacketReader) -> CommandRequest:
        return cls(
            command_line=r.string(),
            command_origin=r.byte_slice(),
            internal=r.bool(),
            version=r.string(),
        )
