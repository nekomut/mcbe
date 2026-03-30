"""Packet: CommandOutput."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_COMMAND_OUTPUT
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CommandOutput(Packet):
    packet_id = ID_COMMAND_OUTPUT
    command_origin: bytes = b""
    output_type: int = 0
    success_count: int = 0
    output_messages: bytes = b""
    data_set: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.command_origin)
        w.uint8(self.output_type)
        w.uint32(self.success_count)
        w.byte_slice(self.output_messages)
        w.byte_slice(self.data_set)

    @classmethod
    def read(cls, r: PacketReader) -> CommandOutput:
        return cls(
            command_origin=r.byte_slice(),
            output_type=r.uint8(),
            success_count=r.uint32(),
            output_messages=r.byte_slice(),
            data_set=r.byte_slice(),
        )
