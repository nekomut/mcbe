"""PlayStatus packet - server sends login/spawn status."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_PLAY_STATUS
from pymc.proto.pool import Packet, register_server_packet

STATUS_LOGIN_SUCCESS = 0
STATUS_LOGIN_FAILED_CLIENT = 1
STATUS_LOGIN_FAILED_SERVER = 2
STATUS_PLAYER_SPAWN = 3
STATUS_LOGIN_FAILED_INVALID_TENANT = 4
STATUS_LOGIN_FAILED_VANILLA_EDU = 5
STATUS_LOGIN_FAILED_EDU_VANILLA = 6
STATUS_LOGIN_FAILED_SERVER_FULL = 7
STATUS_LOGIN_FAILED_EDITOR_VANILLA = 8
STATUS_LOGIN_FAILED_VANILLA_EDITOR = 9


@register_server_packet
@dataclass
class PlayStatus(Packet):
    packet_id = ID_PLAY_STATUS
    status: int = 0

    def write(self, w: PacketWriter) -> None:
        w.be_int32(self.status)

    @classmethod
    def read(cls, r: PacketReader) -> PlayStatus:
        return cls(status=r.be_int32())
