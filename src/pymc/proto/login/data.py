"""Login identity and client data structures.

Mirrors gophertunnel/minecraft/protocol/login/data.go.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IdentityData:
    """Player identity data from Xbox Live / PlayFab authentication."""
    xuid: str = ""
    identity: str = ""  # Player UUID
    display_name: str = ""
    title_id: str = ""
    playfab_title_id: str = ""
    playfab_id: str = ""

    def validate(self) -> None:
        if not self.display_name:
            raise ValueError("display_name must not be empty")
        if len(self.display_name) > 15:
            raise ValueError(
                f"display_name must be at most 15 characters, got {len(self.display_name)}"
            )
        if not self.identity:
            raise ValueError("identity (UUID) must not be empty")


@dataclass
class ClientData:
    """Client data sent during login (device info, skin, etc.)."""
    game_version: str = ""
    server_address: str = ""
    language_code: str = "en_US"
    device_os: int = 0
    device_model: str = ""
    device_id: str = ""
    client_random_id: int = 0
    current_input_mode: int = 0
    default_input_mode: int = 0
    gui_scale: int = 0
    ui_profile: int = 0
    is_editor_mode: bool = False
    skin_id: str = ""
    skin_data: str = ""
    skin_image_height: int = 0
    skin_image_width: int = 0
    skin_resource_patch: str = ""
    skin_geometry: str = ""
    skin_geometry_version: str = ""
    skin_colour: str = ""
    arm_size: str = "wide"
    cape_data: str = ""
    cape_id: str = ""
    cape_image_height: int = 0
    cape_image_width: int = 0
    cape_on_classic_skin: bool = False
    persona_skin: bool = False
    premium_skin: bool = False
    trusted_skin: bool = False
    self_signed_id: str = ""
    platform_offline_id: str = ""
    platform_online_id: str = ""
    platform_user_id: str = ""
    third_party_name: str = ""
    playfab_id: str = ""
    compatible_with_client_side_chunk_gen: bool = False
    max_view_distance: int = 0
    memory_tier: int = 0


@dataclass
class GameData:
    """Game data sent by the server during StartGame."""
    world_name: str = ""
    world_seed: int = 0
    difficulty: int = 0
    entity_unique_id: int = 0
    entity_runtime_id: int = 0
    player_game_mode: int = 0
    player_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    pitch: float = 0.0
    yaw: float = 0.0
    dimension: int = 0
    world_spawn: tuple[int, int, int] = (0, 0, 0)
    world_game_mode: int = 0
    hardcore: bool = False
    base_game_version: str = ""
    time: int = 0
    chunk_radius: int = 0
    server_authoritative_inventory: bool = False
    player_permissions: int = 0
    chat_restriction_level: int = 0
    disable_player_interactions: bool = False
    use_block_network_id_hashes: bool = False
    persona_disabled: bool = False
    custom_skins_disabled: bool = False
