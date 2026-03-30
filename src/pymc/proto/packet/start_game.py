"""Packet: StartGame.

Manually ported from gophertunnel/minecraft/protocol/packet/start_game.go.
This is a critical handshake packet with 79+ fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from pymc.proto.io import PacketReader, PacketWriter
from pymc.proto.packet import ID_START_GAME
from pymc.proto.pool import Packet, register_server_packet
from pymc.proto.types import (
    BlockEntry,
    BlockPos,
    EducationSharedResourceURI,
    ExperimentData,
    GameRule,
    PlayerMovementSettings,
    Vec3,
)

# ── Constants ───────────────────────────────────────────────────

SPAWN_BIOME_TYPE_DEFAULT = 0
SPAWN_BIOME_TYPE_USER_DEFINED = 1

EDITOR_WORLD_TYPE_NOT_EDITOR = 0
EDITOR_WORLD_TYPE_PROJECT = 1
EDITOR_WORLD_TYPE_TEST_LEVEL = 2
EDITOR_WORLD_TYPE_REALMS_UPLOAD = 3

CHAT_RESTRICTION_NONE = 0
CHAT_RESTRICTION_DROPPED = 1
CHAT_RESTRICTION_DISABLED = 2


# ── GameRule serialization (legacy) ─────────────────────────────


def _write_game_rule_legacy(w: PacketWriter, rule: GameRule) -> None:
    w.string(rule.name)
    w.bool(rule.can_be_modified_by_player)
    if isinstance(rule.value, bool):
        w.varuint32(1)
        w.bool(rule.value)
    elif isinstance(rule.value, int):
        w.varuint32(2)
        w.varuint32(rule.value)
    elif isinstance(rule.value, float):
        w.varuint32(3)
        w.float32(rule.value)


def _read_game_rule_legacy(r: PacketReader) -> GameRule:
    name = r.string()
    can_modify = r.bool()
    rule_type = r.varuint32()
    if rule_type == 1:
        value: bool | int | float = r.bool()
    elif rule_type == 2:
        value = r.varuint32()
    elif rule_type == 3:
        value = r.float32()
    else:
        raise ValueError(f"Unknown game rule type: {rule_type}")
    return GameRule(name=name, can_be_modified_by_player=can_modify, value=value)


# ── ExperimentData serialization ────────────────────────────────


def _write_experiment(w: PacketWriter, exp: ExperimentData) -> None:
    w.string(exp.name)
    w.bool(exp.enabled)


def _read_experiment(r: PacketReader) -> ExperimentData:
    return ExperimentData(name=r.string(), enabled=r.bool())


# ── BlockEntry serialization ────────────────────────────────────


def _write_block_entry(w: PacketWriter, entry: BlockEntry) -> None:
    w.string(entry.name)
    w.nbt(entry.properties)


def _read_block_entry(r: PacketReader) -> BlockEntry:
    return BlockEntry(name=r.string(), properties=r.nbt())


@register_server_packet
@dataclass
class StartGame(Packet):
    packet_id = ID_START_GAME

    entity_unique_id: int = 0
    entity_runtime_id: int = 0
    player_game_mode: int = 0
    player_position: Vec3 = field(default_factory=Vec3)
    pitch: float = 0.0
    yaw: float = 0.0
    world_seed: int = 0
    spawn_biome_type: int = 0
    user_defined_biome_name: str = ""
    dimension: int = 0
    generator: int = 0
    world_game_mode: int = 0
    hardcore: bool = False
    difficulty: int = 0
    world_spawn: BlockPos = field(default_factory=BlockPos)
    achievements_disabled: bool = False
    editor_world_type: int = 0
    created_in_editor: bool = False
    exported_from_editor: bool = False
    day_cycle_lock_time: int = 0
    education_edition_offer: int = 0
    education_features_enabled: bool = False
    education_product_id: str = ""
    rain_level: float = 0.0
    lightning_level: float = 0.0
    confirmed_platform_locked_content: bool = False
    multi_player_game: bool = False
    lan_broadcast_enabled: bool = False
    xbl_broadcast_mode: int = 0
    platform_broadcast_mode: int = 0
    commands_enabled: bool = False
    texture_pack_required: bool = False
    game_rules: list[GameRule] = field(default_factory=list)
    experiments: list[ExperimentData] = field(default_factory=list)
    experiments_previously_toggled: bool = False
    bonus_chest_enabled: bool = False
    start_with_map_enabled: bool = False
    player_permissions: int = 0
    server_chunk_tick_radius: int = 0
    has_locked_behaviour_pack: bool = False
    has_locked_texture_pack: bool = False
    from_locked_world_template: bool = False
    msa_gamer_tags_only: bool = False
    from_world_template: bool = False
    world_template_settings_locked: bool = False
    only_spawn_v1_villagers: bool = False
    persona_disabled: bool = False
    custom_skins_disabled: bool = False
    emote_chat_muted: bool = False
    base_game_version: str = ""
    limited_world_width: int = 0
    limited_world_depth: int = 0
    new_nether: bool = False
    education_shared_resource_uri: EducationSharedResourceURI = field(
        default_factory=EducationSharedResourceURI
    )
    force_experimental_gameplay: bool = False
    chat_restriction_level: int = 0
    disable_player_interactions: bool = False
    level_id: str = ""
    world_name: str = ""
    template_content_identity: str = ""
    trial: bool = False
    player_movement_settings: PlayerMovementSettings = field(
        default_factory=PlayerMovementSettings
    )
    time: int = 0
    enchantment_seed: int = 0
    blocks: list[BlockEntry] = field(default_factory=list)
    multi_player_correlation_id: str = ""
    server_authoritative_inventory: bool = False
    game_version: str = ""
    property_data: dict = field(default_factory=dict)
    server_block_state_checksum: int = 0
    world_template_id: UUID = field(default_factory=lambda: UUID(int=0))
    client_side_generation: bool = False
    use_block_network_id_hashes: bool = False
    server_authoritative_sound: bool = False
    # ServerJoinInformation is complex Optional; keep as raw bytes for now
    server_join_information: bytes = b""
    server_id: str = ""
    scenario_id: str = ""
    world_id: str = ""
    owner_id: str = ""

    def write(self, w: PacketWriter) -> None:
        w.varint64(self.entity_unique_id)
        w.varuint64(self.entity_runtime_id)
        w.varint32(self.player_game_mode)
        w.vec3(self.player_position)
        w.float32(self.pitch)
        w.float32(self.yaw)
        w.int64(self.world_seed)
        w.int16(self.spawn_biome_type)
        w.string(self.user_defined_biome_name)
        w.varint32(self.dimension)
        w.varint32(self.generator)
        w.varint32(self.world_game_mode)
        w.bool(self.hardcore)
        w.varint32(self.difficulty)
        w.block_pos(self.world_spawn)
        w.bool(self.achievements_disabled)
        w.varint32(self.editor_world_type)
        w.bool(self.created_in_editor)
        w.bool(self.exported_from_editor)
        w.varint32(self.day_cycle_lock_time)
        w.varint32(self.education_edition_offer)
        w.bool(self.education_features_enabled)
        w.string(self.education_product_id)
        w.float32(self.rain_level)
        w.float32(self.lightning_level)
        w.bool(self.confirmed_platform_locked_content)
        w.bool(self.multi_player_game)
        w.bool(self.lan_broadcast_enabled)
        w.varint32(self.xbl_broadcast_mode)
        w.varint32(self.platform_broadcast_mode)
        w.bool(self.commands_enabled)
        w.bool(self.texture_pack_required)
        # GameRules (legacy format, varuint32 length prefix)
        w.write_slice(self.game_rules, lambda rule: _write_game_rule_legacy(w, rule))
        # Experiments (uint32 length prefix)
        w.write_slice_uint32(self.experiments, lambda exp: _write_experiment(w, exp))
        w.bool(self.experiments_previously_toggled)
        w.bool(self.bonus_chest_enabled)
        w.bool(self.start_with_map_enabled)
        w.varint32(self.player_permissions)
        w.int32(self.server_chunk_tick_radius)
        w.bool(self.has_locked_behaviour_pack)
        w.bool(self.has_locked_texture_pack)
        w.bool(self.from_locked_world_template)
        w.bool(self.msa_gamer_tags_only)
        w.bool(self.from_world_template)
        w.bool(self.world_template_settings_locked)
        w.bool(self.only_spawn_v1_villagers)
        w.bool(self.persona_disabled)
        w.bool(self.custom_skins_disabled)
        w.bool(self.emote_chat_muted)
        w.string(self.base_game_version)
        w.int32(self.limited_world_width)
        w.int32(self.limited_world_depth)
        w.bool(self.new_nether)
        # EducationSharedResourceURI
        w.string(self.education_shared_resource_uri.button_name)
        w.string(self.education_shared_resource_uri.link_uri)
        w.bool(self.force_experimental_gameplay)
        w.uint8(self.chat_restriction_level)
        w.bool(self.disable_player_interactions)
        w.string(self.level_id)
        w.string(self.world_name)
        w.string(self.template_content_identity)
        w.bool(self.trial)
        # PlayerMovementSettings
        w.varint32(self.player_movement_settings.rewind_history_size)
        w.bool(self.player_movement_settings.server_authoritative_block_breaking)
        w.int64(self.time)
        w.varint32(self.enchantment_seed)
        # Blocks (varuint32 length prefix)
        w.write_slice(self.blocks, lambda entry: _write_block_entry(w, entry))
        w.string(self.multi_player_correlation_id)
        w.bool(self.server_authoritative_inventory)
        w.string(self.game_version)
        w.nbt(self.property_data)
        w.uint64(self.server_block_state_checksum)
        w.uuid(self.world_template_id)
        w.bool(self.client_side_generation)
        w.bool(self.use_block_network_id_hashes)
        w.bool(self.server_authoritative_sound)
        # ServerJoinInformation (Optional - raw bytes)
        w.byte_slice(self.server_join_information)
        w.string(self.server_id)
        w.string(self.scenario_id)
        w.string(self.world_id)
        w.string(self.owner_id)

    @classmethod
    def read(cls, r: PacketReader) -> StartGame:
        return cls(
            entity_unique_id=r.varint64(),
            entity_runtime_id=r.varuint64(),
            player_game_mode=r.varint32(),
            player_position=r.vec3(),
            pitch=r.float32(),
            yaw=r.float32(),
            world_seed=r.int64(),
            spawn_biome_type=r.int16(),
            user_defined_biome_name=r.string(),
            dimension=r.varint32(),
            generator=r.varint32(),
            world_game_mode=r.varint32(),
            hardcore=r.bool(),
            difficulty=r.varint32(),
            world_spawn=r.block_pos(),
            achievements_disabled=r.bool(),
            editor_world_type=r.varint32(),
            created_in_editor=r.bool(),
            exported_from_editor=r.bool(),
            day_cycle_lock_time=r.varint32(),
            education_edition_offer=r.varint32(),
            education_features_enabled=r.bool(),
            education_product_id=r.string(),
            rain_level=r.float32(),
            lightning_level=r.float32(),
            confirmed_platform_locked_content=r.bool(),
            multi_player_game=r.bool(),
            lan_broadcast_enabled=r.bool(),
            xbl_broadcast_mode=r.varint32(),
            platform_broadcast_mode=r.varint32(),
            commands_enabled=r.bool(),
            texture_pack_required=r.bool(),
            game_rules=r.read_slice(lambda: _read_game_rule_legacy(r)),
            experiments=r.read_slice_uint32(lambda: _read_experiment(r)),
            experiments_previously_toggled=r.bool(),
            bonus_chest_enabled=r.bool(),
            start_with_map_enabled=r.bool(),
            player_permissions=r.varint32(),
            server_chunk_tick_radius=r.int32(),
            has_locked_behaviour_pack=r.bool(),
            has_locked_texture_pack=r.bool(),
            from_locked_world_template=r.bool(),
            msa_gamer_tags_only=r.bool(),
            from_world_template=r.bool(),
            world_template_settings_locked=r.bool(),
            only_spawn_v1_villagers=r.bool(),
            persona_disabled=r.bool(),
            custom_skins_disabled=r.bool(),
            emote_chat_muted=r.bool(),
            base_game_version=r.string(),
            limited_world_width=r.int32(),
            limited_world_depth=r.int32(),
            new_nether=r.bool(),
            education_shared_resource_uri=EducationSharedResourceURI(
                button_name=r.string(),
                link_uri=r.string(),
            ),
            force_experimental_gameplay=r.bool(),
            chat_restriction_level=r.uint8(),
            disable_player_interactions=r.bool(),
            level_id=r.string(),
            world_name=r.string(),
            template_content_identity=r.string(),
            trial=r.bool(),
            player_movement_settings=PlayerMovementSettings(
                rewind_history_size=r.varint32(),
                server_authoritative_block_breaking=r.bool(),
            ),
            time=r.int64(),
            enchantment_seed=r.varint32(),
            blocks=r.read_slice(lambda: _read_block_entry(r)),
            multi_player_correlation_id=r.string(),
            server_authoritative_inventory=r.bool(),
            game_version=r.string(),
            property_data=r.nbt(),
            server_block_state_checksum=r.uint64(),
            world_template_id=r.uuid(),
            client_side_generation=r.bool(),
            use_block_network_id_hashes=r.bool(),
            server_authoritative_sound=r.bool(),
            server_join_information=r.byte_slice(),
            server_id=r.string(),
            scenario_id=r.string(),
            world_id=r.string(),
            owner_id=r.string(),
        )
