"""Packet: NPCDialogue."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_NPC_DIALOGUE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class NPCDialogue(Packet):
    packet_id = ID_NPC_DIALOGUE
    entity_unique_id: int = 0
    action_type: int = 0
    dialogue: str = ""
    scene_name: str = ""
    npc_name: str = ""
    action_json: str = ""

    def write(self, w: PacketWriter) -> None:
        w.uint64(self.entity_unique_id)
        w.varint32(self.action_type)
        w.string(self.dialogue)
        w.string(self.scene_name)
        w.string(self.npc_name)
        w.string(self.action_json)

    @classmethod
    def read(cls, r: PacketReader) -> NPCDialogue:
        return cls(
            entity_unique_id=r.uint64(),
            action_type=r.varint32(),
            dialogue=r.string(),
            scene_name=r.string(),
            npc_name=r.string(),
            action_json=r.string(),
        )
