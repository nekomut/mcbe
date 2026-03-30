"""Packet: PlayerVideoCapture."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAYER_VIDEO_CAPTURE
from pymc.proto.pool import Packet, register_server_packet

PLAYER_VIDEO_CAPTURE_ACTION_STOP = 0
PLAYER_VIDEO_CAPTURE_ACTION_START = 1


@register_server_packet
@dataclass
class PlayerVideoCapture(Packet):
    packet_id = ID_PLAYER_VIDEO_CAPTURE
    action: int = 0
    frame_rate: int = 0
    file_prefix: str = ""

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.action)
        if self.action == PLAYER_VIDEO_CAPTURE_ACTION_START:
            w.int32(self.frame_rate)
            w.string(self.file_prefix)

    @classmethod
    def read(cls, r: PacketReader) -> PlayerVideoCapture:
        action = r.uint8()
        frame_rate = 0
        file_prefix = ""
        if action == PLAYER_VIDEO_CAPTURE_ACTION_START:
            frame_rate = r.int32()
            file_prefix = r.string()
        return cls(
            action=action,
            frame_rate=frame_rate,
            file_prefix=file_prefix,
        )
