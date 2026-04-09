"""Basic Minecraft protocol types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple
from uuid import UUID


class BlockPos(NamedTuple):
    """Block position as three signed 32-bit integers (x, y, z)."""
    x: int = 0
    y: int = 0
    z: int = 0


class ChunkPos(NamedTuple):
    """Chunk position as two signed 32-bit integers (x, z)."""
    x: int = 0
    z: int = 0


class SubChunkPos(NamedTuple):
    """Sub-chunk position as three signed 32-bit integers (x, y, z)."""
    x: int = 0
    y: int = 0
    z: int = 0


class Vec2(NamedTuple):
    """2D vector of float32 values."""
    x: float = 0.0
    y: float = 0.0


class Vec3(NamedTuple):
    """3D vector of float32 values."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class RGBA:
    """RGBA colour value."""
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255

    def to_uint32(self) -> int:
        """Encode as little-endian uint32 (RGBA byte order used in protocol)."""
        return self.r | (self.g << 8) | (self.b << 16) | (self.a << 24)

    @classmethod
    def from_uint32(cls, v: int) -> RGBA:
        return cls(r=v & 0xFF, g=(v >> 8) & 0xFF, b=(v >> 16) & 0xFF, a=(v >> 24) & 0xFF)


@dataclass
class GameRule:
    """A single game rule with name, editable flag, and value."""
    name: str = ""
    can_be_modified_by_player: bool = False
    value: bool | int | float = False


@dataclass
class Attribute:
    """An entity attribute (e.g. health, hunger)."""
    name: str = ""
    value: float = 0.0
    max: float = 0.0
    min: float = 0.0
    default: float = 0.0


@dataclass
class AttributeModifier:
    """A modifier applied to an attribute."""
    id: str = ""
    name: str = ""
    amount: float = 0.0
    operation: int = 0
    operand: int = 0
    serializable: bool = False


@dataclass
class AttributeValue:
    """An attribute with its modifiers."""
    name: str = ""
    min: float = 0.0
    max: float = 0.0
    value: float = 0.0
    default: float = 0.0
    modifiers: list[AttributeModifier] = field(default_factory=list)


@dataclass
class AbilityLayer:
    """A layer in the ability system."""
    layer_type: int = 0
    abilities: int = 0
    values: int = 0
    fly_speed: float = 0.0
    walk_speed: float = 0.0


@dataclass
class AbilityData:
    """Player ability data."""
    entity_unique_id: int = 0
    player_permissions: int = 0
    command_permissions: int = 0
    layers: list[AbilityLayer] = field(default_factory=list)


@dataclass
class EntityLink:
    """A link between two entities (e.g. riding)."""
    ridden_entity_unique_id: int = 0
    rider_entity_unique_id: int = 0
    link_type: int = 0
    immediate: bool = False
    rider_initiated: bool = False


@dataclass
class ItemStack:
    """A stack of items in an inventory slot."""
    network_id: int = 0
    count: int = 0
    metadata: int = 0
    has_net_id: bool = False
    net_id: int = 0
    block_runtime_id: int = 0
    extra: bytes = b""


@dataclass
class ItemInstance:
    """An item instance with stack ID information."""
    stack_network_id: int = 0
    stack: ItemStack = field(default_factory=ItemStack)


@dataclass
class ItemDescriptorCount:
    """An item descriptor with a count."""
    descriptor_type: int = 0
    data: bytes = b""
    count: int = 0


@dataclass
class PackSetting:
    """Pack setting for a resource/behaviour pack."""
    uuid: str = ""
    version: str = ""
    sub_pack_name: str = ""


@dataclass
class StackRequestAction:
    """Base for item stack request actions."""
    action_type: int = 0
    data: bytes = b""


@dataclass
class MaterialReducer:
    """Material reducer recipe data."""
    network_id: int = 0
    items: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class ExperimentData:
    """An experiment that may be enabled or disabled."""
    name: str = ""
    enabled: bool = False


@dataclass
class EducationSharedResourceURI:
    """Education edition shared resource URI."""
    button_name: str = ""
    link_uri: str = ""


@dataclass
class PlayerMovementSettings:
    """Player movement settings."""
    rewind_history_size: int = 0
    server_authoritative_block_breaking: bool = False


@dataclass
class BlockEntry:
    """A custom block entry with name and NBT properties."""
    name: str = ""
    properties: dict = field(default_factory=dict)
    properties_typed: dict | None = field(default=None, repr=False)
