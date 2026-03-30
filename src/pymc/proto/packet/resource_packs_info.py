"""Packet: ResourcePacksInfo."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_RESOURCE_PACKS_INFO
from pymc.proto.pool import Packet, register_server_packet


@register_server_packet
@dataclass
class ResourcePacksInfo(Packet):
    packet_id = ID_RESOURCE_PACKS_INFO
    texture_pack_required: bool = False
    has_addons: bool = False
    has_scripts: bool = False
    force_disable_vibrant_visuals: bool = False
    world_template_uuid: UUID = 0
    world_template_version: str = ""
    texture_packs: bytes = b""

    def write(self, w: PacketWriter) -> None:
        w.bool(self.texture_pack_required)
        w.bool(self.has_addons)
        w.bool(self.has_scripts)
        w.bool(self.force_disable_vibrant_visuals)
        w.uuid(self.world_template_uuid)
        w.string(self.world_template_version)
        w.byte_slice(self.texture_packs)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePacksInfo:
        return cls(
            texture_pack_required=r.bool(),
            has_addons=r.bool(),
            has_scripts=r.bool(),
            force_disable_vibrant_visuals=r.bool(),
            world_template_uuid=r.uuid(),
            world_template_version=r.string(),
            texture_packs=r.byte_slice(),
        )
