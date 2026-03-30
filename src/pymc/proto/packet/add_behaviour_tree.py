"""Packet: AddBehaviourTree."""

from __future__ import annotations

from dataclasses import dataclass

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_ADD_BEHAVIOUR_TREE
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class AddBehaviourTree(Packet):
    packet_id = ID_ADD_BEHAVIOUR_TREE
    behaviour_tree: str = ""

    def write(self, w: PacketWriter) -> None:
        w.string(self.behaviour_tree)

    @classmethod
    def read(cls, r: PacketReader) -> AddBehaviourTree:
        return cls(
            behaviour_tree=r.string(),
        )
