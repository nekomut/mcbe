"""Packet: PlayerList.

Entry structures (PlayerListEntry) are kept as raw bytes because the
full PlayerListEntry type with Skin sub-structures has not been ported yet.
The conditional logic for Add vs Remove action types is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_LIST
from pymc.proto.pool import Packet, register_server_packet

PLAYER_LIST_ACTION_ADD = 0
PLAYER_LIST_ACTION_REMOVE = 1


@register_server_packet
@dataclass
class PlayerList(Packet):
    packet_id = ID_PLAYER_LIST
    action_type: int = 0
    entries: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action_type)
        w.bytes_raw(self.entries)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerList:
        action_type = r.uint8()
        entries = r.bytes_remaining()
        return cls(
            action_type=action_type,
            entries=entries,
        )
