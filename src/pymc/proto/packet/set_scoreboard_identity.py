"""Packet: SetScoreboardIdentity.

ScoreboardIdentityEntry structures are kept as raw bytes because the full
type has not been ported yet. The conditional logic for Register vs Clear
action types is noted.
"""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_SET_SCOREBOARD_IDENTITY
from pymc.proto.pool import Packet, register_server_packet

SCOREBOARD_IDENTITY_ACTION_REGISTER = 0
SCOREBOARD_IDENTITY_ACTION_CLEAR = 1


@register_server_packet
@dataclass
class SetScoreboardIdentity(Packet):
    packet_id = ID_SET_SCOREBOARD_IDENTITY
    action_type: int = 0
    entries: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_type)
        w.bytes_raw(self.entries)

    @classmethod
    def read(cls, r: PacketReader) -> SetScoreboardIdentity:
        action_type = r.uint8()
        entries = r.bytes_remaining()
        return cls(
            action_type=action_type,
            entries=entries,
        )
