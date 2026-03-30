"""Resource pack related packets."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import (
    ID_RESOURCE_PACK_CLIENT_RESPONSE,
    ID_RESOURCE_PACK_STACK,
    ID_RESOURCE_PACKS_INFO,
)
from pymc.proto.pool import Packet, register_bidirectional, register_server_packet

# ResourcePackClientResponse constants
PACK_RESPONSE_REFUSED = 1
PACK_RESPONSE_SEND_PACKS = 2
PACK_RESPONSE_ALL_PACKS_DOWNLOADED = 3
PACK_RESPONSE_COMPLETED = 4


@dataclass
class TexturePackInfo:
    """Information about a texture/resource pack."""
    uuid: str = ""
    version: str = ""
    size: int = 0
    content_key: str = ""
    sub_pack_name: str = ""
    content_identity: str = ""
    has_scripts: bool = False
    addon_pack: bool = False
    rtx_enabled: bool = False


@dataclass
class StackResourcePack:
    """A resource pack in the resource pack stack."""
    uuid: str = ""
    version: str = ""
    sub_pack_name: str = ""


@dataclass
class ExperimentData:
    """Data for an experiment toggle."""
    name: str = ""
    enabled: bool = False


def _read_texture_pack_info(r: PacketReader) -> TexturePackInfo:
    return TexturePackInfo(
        uuid=r.string(),
        version=r.string(),
        size=r.uint64(),
        content_key=r.string(),
        sub_pack_name=r.string(),
        content_identity=r.string(),
        has_scripts=r.bool(),
        addon_pack=r.bool(),
        rtx_enabled=r.bool(),
    )


def _write_texture_pack_info(w: PacketWriter, info: TexturePackInfo) -> None:
    w.string(info.uuid)
    w.string(info.version)
    w.uint64(info.size)
    w.string(info.content_key)
    w.string(info.sub_pack_name)
    w.string(info.content_identity)
    w.bool(info.has_scripts)
    w.bool(info.addon_pack)
    w.bool(info.rtx_enabled)


def _read_stack_resource_pack(r: PacketReader) -> StackResourcePack:
    return StackResourcePack(
        uuid=r.string(),
        version=r.string(),
        sub_pack_name=r.string(),
    )


def _write_stack_resource_pack(w: PacketWriter, pack: StackResourcePack) -> None:
    w.string(pack.uuid)
    w.string(pack.version)
    w.string(pack.sub_pack_name)


def _read_experiment(r: PacketReader) -> ExperimentData:
    return ExperimentData(name=r.string(), enabled=r.bool())


def _write_experiment(w: PacketWriter, exp: ExperimentData) -> None:
    w.string(exp.name)
    w.bool(exp.enabled)


@register_server_packet
@dataclass
class ResourcePacksInfo(Packet):
    packet_id = ID_RESOURCE_PACKS_INFO
    texture_pack_required: bool = False
    has_addons: bool = False
    has_scripts: bool = False
    force_disable_vibrant_visuals: bool = False
    world_template_uuid: UUID = field(default_factory=lambda: UUID(int=0))
    world_template_version: str = ""
    texture_packs: list[TexturePackInfo] = field(default_factory=list)

    def write(self, w: PacketWriter) -> None:
        w.bool(self.texture_pack_required)
        w.bool(self.has_addons)
        w.bool(self.has_scripts)
        w.bool(self.force_disable_vibrant_visuals)
        w.uuid(self.world_template_uuid)
        w.string(self.world_template_version)
        w.uint16(len(self.texture_packs))
        for pack in self.texture_packs:
            _write_texture_pack_info(w, pack)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePacksInfo:
        texture_pack_required = r.bool()
        has_addons = r.bool()
        has_scripts = r.bool()
        force_disable_vibrant_visuals = r.bool()
        world_template_uuid = r.uuid()
        world_template_version = r.string()
        texture_packs = r.read_slice_uint16(lambda: _read_texture_pack_info(r))
        return cls(
            texture_pack_required=texture_pack_required,
            has_addons=has_addons,
            has_scripts=has_scripts,
            force_disable_vibrant_visuals=force_disable_vibrant_visuals,
            world_template_uuid=world_template_uuid,
            world_template_version=world_template_version,
            texture_packs=texture_packs,
        )


@register_server_packet
@dataclass
class ResourcePackStack(Packet):
    packet_id = ID_RESOURCE_PACK_STACK
    texture_pack_required: bool = False
    texture_packs: list[StackResourcePack] = field(default_factory=list)
    base_game_version: str = ""
    experiments: list[ExperimentData] = field(default_factory=list)
    experiments_previously_toggled: bool = False
    include_editor_packs: bool = False

    def write(self, w: PacketWriter) -> None:
        w.bool(self.texture_pack_required)
        w.write_slice(self.texture_packs, lambda p: _write_stack_resource_pack(w, p))
        w.string(self.base_game_version)
        w.write_slice_uint32(self.experiments, lambda e: _write_experiment(w, e))
        w.bool(self.experiments_previously_toggled)
        w.bool(self.include_editor_packs)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePackStack:
        return cls(
            texture_pack_required=r.bool(),
            texture_packs=r.read_slice(lambda: _read_stack_resource_pack(r)),
            base_game_version=r.string(),
            experiments=r.read_slice_uint32(lambda: _read_experiment(r)),
            experiments_previously_toggled=r.bool(),
            include_editor_packs=r.bool(),
        )


@register_bidirectional
@dataclass
class ResourcePackClientResponse(Packet):
    packet_id = ID_RESOURCE_PACK_CLIENT_RESPONSE
    response: int = 0
    packs_to_download: list[str] = field(default_factory=list)

    def write(self, w: PacketWriter) -> None:
        w.uint8(self.response)
        w.write_slice_uint16(self.packs_to_download, w.string)

    @classmethod
    def read(cls, r: PacketReader) -> ResourcePackClientResponse:
        return cls(
            response=r.uint8(),
            packs_to_download=r.read_slice_uint16(r.string),
        )
