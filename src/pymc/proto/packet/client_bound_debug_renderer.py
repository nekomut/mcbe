"""Packet: ClientBoundDebugRenderer."""

from __future__ import annotations

from dataclasses import dataclass, field

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_CLIENT_BOUND_DEBUG_RENDERER
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import Vec3

CLIENT_BOUND_DEBUG_RENDERER_CLEAR = 0
CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE = 1

_TYPE_TO_STRING = {
    CLIENT_BOUND_DEBUG_RENDERER_CLEAR: "cleardebugmarkers",
    CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE: "adddebugmarkercube",
}
_STRING_TO_TYPE = {v: k for k, v in _TYPE_TO_STRING.items()}


@register_server_packet
@dataclass
class ClientBoundDebugRenderer(Packet):
    packet_id = ID_CLIENT_BOUND_DEBUG_RENDERER
    type: int = 0
    text: str = ""
    position: Vec3 = field(default_factory=lambda: Vec3(0.0, 0.0, 0.0))
    red: float = 0.0
    green: float = 0.0
    blue: float = 0.0
    alpha: float = 0.0
    duration: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(_TYPE_TO_STRING.get(self.type, "unknown"))
        if self.type == CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE:
            w.string(self.text)
            w.vec3(self.position)
            w.float32(self.red)
            w.float32(self.green)
            w.float32(self.blue)
            w.float32(self.alpha)
            w.uint64(self.duration)

    @classmethod
    def read(cls, r: PacketReader) -> ClientBoundDebugRenderer:
        type_str = r.string()
        type_ = _STRING_TO_TYPE.get(type_str, 0)
        text = ""
        position = Vec3(0.0, 0.0, 0.0)
        red = 0.0
        green = 0.0
        blue = 0.0
        alpha = 0.0
        duration = 0
        if type_ == CLIENT_BOUND_DEBUG_RENDERER_ADD_CUBE:
            text = r.string()
            position = r.vec3()
            red = r.float32()
            green = r.float32()
            blue = r.float32()
            alpha = r.float32()
            duration = r.uint64()
        return cls(
            type=type_,
            text=text,
            position=position,
            red=red,
            green=green,
            blue=blue,
            alpha=alpha,
            duration=duration,
        )
