"""Packet: CommandRequest."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, field

from mcbe.proto.io import PacketReader, PacketWriter
from mcbe.proto.packet import ID_COMMAND_REQUEST
from mcbe.proto.pool import Packet, register_server_packet

# CommandOrigin constants
ORIGIN_PLAYER = "player"
ORIGIN_COMMAND_BLOCK = "commandblock"
ORIGIN_DEV_CONSOLE = "devconsole"
ORIGIN_AUTOMATION_PLAYER = "automationplayer"
ORIGIN_DEDICATED_SERVER = "dedicatedserver"
ORIGIN_ENTITY = "entity"
ORIGIN_SCRIPTING = "scripting"


@dataclass
class CommandOrigin:
    """Command origin data sent with CommandRequest."""

    origin: str = ORIGIN_PLAYER
    uuid: _uuid.UUID = field(default_factory=_uuid.uuid4)
    request_id: str = ""
    player_unique_id: int = 0

    def write(self, w: PacketWriter) -> None:
        w.string(self.origin)
        w.uuid(self.uuid)
        w.string(self.request_id)
        w.int64(self.player_unique_id)

    @classmethod
    def read(cls, r: PacketReader) -> CommandOrigin:
        return cls(
            origin=r.string(),
            uuid=r.uuid(),
            request_id=r.string(),
            player_unique_id=r.int64(),
        )


@register_server_packet
@dataclass
class CommandRequest(Packet):
    packet_id = ID_COMMAND_REQUEST
    command_line: str = ""
    command_origin: CommandOrigin = field(default_factory=CommandOrigin)
    internal: bool = False
    version: str = "latest"

    def write(self, w: PacketWriter) -> None:
        w.string(self.command_line)
        self.command_origin.write(w)
        w.bool(self.internal)
        w.string(self.version)

    @classmethod
    def read(cls, r: PacketReader) -> CommandRequest:
        return cls(
            command_line=r.string(),
            command_origin=CommandOrigin.read(r),
            internal=r.bool(),
            version=r.string(),
        )
