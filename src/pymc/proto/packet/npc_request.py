"""Packet: NPCRequest."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_NPC_REQUEST
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class NPCRequest(Packet):
    packet_id = ID_NPC_REQUEST
    entity_runtime_id: int = 0
    request_type: int = 0
    command_string: str = ""
    action_type: int = 0
    scene_name: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varuint64(self.entity_runtime_id)
        w.uint8(self.request_type)
        w.string(self.command_string)
        w.uint8(self.action_type)
        w.string(self.scene_name)

    @classmethod
    def read(cls, r: PacketReader) -> NPCRequest:
        return cls(
            entity_runtime_id=r.varuint64(),
            request_type=r.uint8(),
            command_string=r.string(),
            action_type=r.uint8(),
            scene_name=r.string(),
        )
