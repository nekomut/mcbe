"""Packet: GraphicsOverrideParameter."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_GRAPHICS_OVERRIDE_PARAMETER
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class GraphicsOverrideParameter(Packet):
    packet_id = ID_GRAPHICS_OVERRIDE_PARAMETER
    values: bytes = b""
    float_value: bytes = b""
    vec3_value: bytes = b""
    biome_identifier: str = ""
    parameter_type: int = 0
    reset: bool = False

    def write(self, w: PacketWriter) -> None:
        w.byte_slice(self.values)
        w.byte_slice(self.float_value)
        w.byte_slice(self.vec3_value)
        w.string(self.biome_identifier)
        w.uint8(self.parameter_type)
        w.bool(self.reset)

    @classmethod
    def read(cls, r: PacketReader) -> GraphicsOverrideParameter:
        return cls(
            values=r.byte_slice(),
            float_value=r.byte_slice(),
            vec3_value=r.byte_slice(),
            biome_identifier=r.string(),
            parameter_type=r.uint8(),
            reset=r.bool(),
        )
