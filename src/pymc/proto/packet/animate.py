"""Packet: Animate."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ANIMATE
from pymc.proto.pool import Packet, register_server_packet

ANIMATE_ACTION_SWING_ARM = 1
ANIMATE_ACTION_STOP_SLEEP = 3
ANIMATE_ACTION_CRITICAL_HIT = 4
ANIMATE_ACTION_MAGIC_CRITICAL_HIT = 5

ANIMATE_SWING_SOURCE_NONE = 1
ANIMATE_SWING_SOURCE_BUILD = 2
ANIMATE_SWING_SOURCE_MINE = 3
ANIMATE_SWING_SOURCE_INTERACT = 4
ANIMATE_SWING_SOURCE_ATTACK = 5
ANIMATE_SWING_SOURCE_USE_ITEM = 6
ANIMATE_SWING_SOURCE_THROW_ITEM = 7
ANIMATE_SWING_SOURCE_DROP_ITEM = 8
ANIMATE_SWING_SOURCE_EVENT = 9

_SWING_SOURCE_TO_STRING = {
    ANIMATE_SWING_SOURCE_NONE: "none",
    ANIMATE_SWING_SOURCE_BUILD: "build",
    ANIMATE_SWING_SOURCE_MINE: "mine",
    ANIMATE_SWING_SOURCE_INTERACT: "interact",
    ANIMATE_SWING_SOURCE_ATTACK: "attack",
    ANIMATE_SWING_SOURCE_USE_ITEM: "useitem",
    ANIMATE_SWING_SOURCE_THROW_ITEM: "throwitem",
    ANIMATE_SWING_SOURCE_DROP_ITEM: "dropitem",
    ANIMATE_SWING_SOURCE_EVENT: "event",
}
_STRING_TO_SWING_SOURCE = {v: k for k, v in _SWING_SOURCE_TO_STRING.items()}


@register_server_packet
@dataclass
class Animate(Packet):
    packet_id = ID_ANIMATE
    action_type: int = 0
    entity_runtime_id: int = 0
    data: float = 0.0
    swing_source: int = 0

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_type)
        w.varuint64(self.entity_runtime_id)
        w.float32(self.data)
        if self.swing_source != 0:
            s = _SWING_SOURCE_TO_STRING.get(self.swing_source, "unknown")
            w.write_optional(s, w.string)
        else:
            w.write_optional(None, w.string)

    @classmethod
    def read(cls, r: PacketReader) -> Animate:
        action_type = r.uint8()
        entity_runtime_id = r.varuint64()
        data = r.float32()
        swing_source_str = r.read_optional(r.string)
        swing_source = 0
        if swing_source_str is not None:
            swing_source = _STRING_TO_SWING_SOURCE.get(swing_source_str, 0)
        return cls(
            action_type=action_type,
            entity_runtime_id=entity_runtime_id,
            data=data,
            swing_source=swing_source,
        )
