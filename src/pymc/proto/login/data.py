"""Login identity and client data structures.

Mirrors gophertunnel/minecraft/protocol/login/data.go.
"""

from __future__ import annotations

import base64
import json
import random
import uuid
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


# Default skin resource patch (references geometry.humanoid.custom).
_SKIN_RESOURCE_PATCH = json.dumps(
    {"geometry": {"default": "geometry.humanoid.custom"}},
    separators=(",", ":"),
)

# Default skin geometry (cape + humanoid.custom + humanoid.customSlim).
# Matches gophertunnel's embedded skin_geometry.json.
_SKIN_GEOMETRY = json.dumps(
    {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "bones": [
                    {"name": "body", "parent": "waist", "pivot": [0, 24, 0]},
                    {"name": "waist", "pivot": [0, 12, 0]},
                    {
                        "cubes": [{"origin": [-5, 8, 3], "size": [10, 16, 1], "uv": [0, 0]}],
                        "name": "cape", "parent": "body",
                        "pivot": [0, 24, 3], "rotation": [0, 180, 0],
                    },
                ],
                "description": {
                    "identifier": "geometry.cape",
                    "texture_height": 32, "texture_width": 64,
                },
            },
            {
                "bones": [
                    {"name": "root", "pivot": [0, 0, 0]},
                    {"cubes": [{"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 16]}], "name": "body", "parent": "waist", "pivot": [0, 24, 0]},
                    {"name": "waist", "parent": "root", "pivot": [0, 12, 0]},
                    {"cubes": [{"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [0, 0]}], "name": "head", "parent": "body", "pivot": [0, 24, 0]},
                    {"name": "cape", "parent": "body", "pivot": [0, 24, 3]},
                    {"cubes": [{"inflate": 0.5, "origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [32, 0]}], "name": "hat", "parent": "head", "pivot": [0, 24, 0]},
                    {"cubes": [{"origin": [4, 12, -2], "size": [4, 12, 4], "uv": [32, 48]}], "name": "leftArm", "parent": "body", "pivot": [5, 22, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [4, 12, -2], "size": [4, 12, 4], "uv": [48, 48]}], "name": "leftSleeve", "parent": "leftArm", "pivot": [5, 22, 0]},
                    {"name": "leftItem", "parent": "leftArm", "pivot": [6, 15, 1]},
                    {"cubes": [{"origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 16]}], "name": "rightArm", "parent": "body", "pivot": [-5, 22, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-8, 12, -2], "size": [4, 12, 4], "uv": [40, 32]}], "name": "rightSleeve", "parent": "rightArm", "pivot": [-5, 22, 0]},
                    {"locators": {"lead_hold": [-6, 15, 1]}, "name": "rightItem", "parent": "rightArm", "pivot": [-6, 15, 1]},
                    {"cubes": [{"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [16, 48]}], "name": "leftLeg", "parent": "root", "pivot": [1.9, 12, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [0, 48]}], "name": "leftPants", "parent": "leftLeg", "pivot": [1.9, 12, 0]},
                    {"cubes": [{"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}], "name": "rightLeg", "parent": "root", "pivot": [-1.9, 12, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 32]}], "name": "rightPants", "parent": "rightLeg", "pivot": [-1.9, 12, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 32]}], "name": "jacket", "parent": "body", "pivot": [0, 24, 0]},
                ],
                "description": {
                    "identifier": "geometry.humanoid.custom",
                    "texture_height": 64, "texture_width": 64,
                    "visible_bounds_height": 2, "visible_bounds_offset": [0, 1, 0], "visible_bounds_width": 1,
                },
            },
            {
                "bones": [
                    {"name": "root", "pivot": [0, 0, 0]},
                    {"name": "waist", "parent": "root", "pivot": [0, 12, 0]},
                    {"cubes": [{"origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 16]}], "name": "body", "parent": "waist", "pivot": [0, 24, 0]},
                    {"cubes": [{"origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [0, 0]}], "name": "head", "parent": "body", "pivot": [0, 24, 0]},
                    {"cubes": [{"inflate": 0.5, "origin": [-4, 24, -4], "size": [8, 8, 8], "uv": [32, 0]}], "name": "hat", "parent": "head", "pivot": [0, 24, 0]},
                    {"cubes": [{"origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 16]}], "name": "rightLeg", "parent": "root", "pivot": [-1.9, 12, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-3.9, 0, -2], "size": [4, 12, 4], "uv": [0, 32]}], "name": "rightPants", "parent": "rightLeg", "pivot": [-1.9, 12, 0]},
                    {"cubes": [{"origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [16, 48]}], "mirror": True, "name": "leftLeg", "parent": "root", "pivot": [1.9, 12, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-0.1, 0, -2], "size": [4, 12, 4], "uv": [0, 48]}], "name": "leftPants", "parent": "leftLeg", "pivot": [1.9, 12, 0]},
                    {"cubes": [{"origin": [4, 11.5, -2], "size": [3, 12, 4], "uv": [32, 48]}], "name": "leftArm", "parent": "body", "pivot": [5, 21.5, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [4, 11.5, -2], "size": [3, 12, 4], "uv": [48, 48]}], "name": "leftSleeve", "parent": "leftArm", "pivot": [5, 21.5, 0]},
                    {"name": "leftItem", "parent": "leftArm", "pivot": [6, 14.5, 1]},
                    {"cubes": [{"origin": [-7, 11.5, -2], "size": [3, 12, 4], "uv": [40, 16]}], "name": "rightArm", "parent": "body", "pivot": [-5, 21.5, 0]},
                    {"cubes": [{"inflate": 0.25, "origin": [-7, 11.5, -2], "size": [3, 12, 4], "uv": [40, 32]}], "name": "rightSleeve", "parent": "rightArm", "pivot": [-5, 21.5, 0]},
                    {"locators": {"lead_hold": [-6, 14.5, 1]}, "name": "rightItem", "parent": "rightArm", "pivot": [-6, 14.5, 1]},
                    {"cubes": [{"inflate": 0.25, "origin": [-4, 12, -2], "size": [8, 12, 4], "uv": [16, 32]}], "name": "jacket", "parent": "body", "pivot": [0, 24, 0]},
                    {"name": "cape", "parent": "body", "pivot": [0, 24, -3]},
                ],
                "description": {
                    "identifier": "geometry.humanoid.customSlim",
                    "texture_height": 64, "texture_width": 64,
                    "visible_bounds_height": 2, "visible_bounds_offset": [0, 1, 0], "visible_bounds_width": 1,
                },
            },
        ],
    },
    separators=(",", ":"),
)


def default_client_data() -> ClientData:
    """Create ClientData with valid defaults matching gophertunnel's defaultClientData().

    Provides a minimal but valid 32x64 black skin with standard humanoid geometry.
    """
    # 32x64 opaque black skin (RGBA 0,0,0,255 per pixel).
    skin_pixels = bytes([0, 0, 0, 255]) * (32 * 64)
    skin_data_b64 = base64.b64encode(skin_pixels).decode()

    return ClientData(
        game_version="1.26.12",
        language_code="en_US",
        device_os=7,  # Windows 10
        device_model="pymc",
        device_id=str(uuid.uuid4()),
        client_random_id=random.randint(-(2**63), 2**63 - 1),
        self_signed_id=str(uuid.uuid4()),
        skin_id=str(uuid.uuid4()),
        skin_data=skin_data_b64,
        skin_image_height=32,
        skin_image_width=64,
        skin_resource_patch=base64.b64encode(_SKIN_RESOURCE_PATCH.encode()).decode(),
        skin_geometry=base64.b64encode(_SKIN_GEOMETRY.encode()).decode(),
        skin_geometry_version=base64.b64encode(b"0.0.0").decode(),
        arm_size="wide",
    )
