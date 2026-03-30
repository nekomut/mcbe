"""Packet: CodeBuilder."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CODE_BUILDER
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class CodeBuilder(Packet):
    packet_id = ID_CODE_BUILDER
    url: str = ""
    should_open_code_builder: bool = False

    def write(self, w: PacketWriter) -> None:
        w.string(self.url)
        w.bool(self.should_open_code_builder)

    @classmethod
    def read(cls, r: PacketReader) -> CodeBuilder:
        return cls(
            url=r.string(),
            should_open_code_builder=r.bool(),
        )
