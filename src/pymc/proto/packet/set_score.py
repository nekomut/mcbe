"""Packet: SetScore.

ScoreboardEntry structures are kept as raw bytes because the full
type has not been ported yet. The conditional logic for Modify vs Remove
action types is noted.
"""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_SCORE
from pymc.proto.pool import Packet, register_server_packet

SCOREBOARD_ACTION_MODIFY = 0
SCOREBOARD_ACTION_REMOVE = 1


@register_server_packet
@dataclass
class SetScore(Packet):
    packet_id = ID_SET_SCORE
    action_type: int = 0
    entries: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_type)
        w.bytes_raw(self.entries)

    @classmethod
    def read(cls, r: PacketReader) -> SetScore:
        action_type = r.uint8()
        entries = r.bytes_remaining()
        return cls(
            action_type=action_type,
            entries=entries,
        )
