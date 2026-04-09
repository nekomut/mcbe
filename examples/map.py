"""リアルタイム地図ビューア.

ワールドに bot として接続し、周辺の地図をブラウザにリアルタイム表示する。
全プレイヤーの周囲を巡回テレポートでカバーする。

Usage:
    # BDS に接続
    python examples/map.py --bds-address 127.0.0.1:19132

    # Realms に接続
    python examples/map.py --realms

    # proxy モード
    python examples/map.py --proxy --listen 0.0.0.0:19133 --remote 127.0.0.1:19132

    ブラウザで http://localhost:8080 を開く
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import uuid as _uuid
from dataclasses import dataclass, field
from pathlib import Path

import aiohttp
from aiohttp import web
from cryptography.hazmat.primitives.asymmetric import ec

from mcbe.chunk import (
    AIR,
    compute_block_hash,
    compute_block_hash_typed,
    load_canonical_block_hashes,
    parse_level_chunk_top_blocks,
    parse_sub_chunk_entries,
    _extract_top_blocks,
)
from mcbe.conn import Connection
from mcbe.dial import Dialer
from mcbe.proto.login.data import IdentityData
from mcbe.proto.packet.command_request import (
    CommandOrigin,
    CommandRequest,
    ORIGIN_AUTOMATION_PLAYER,
)
from mcbe.proto.packet.command_output import CommandOutput
from mcbe.proto.packet.level_chunk import (
    LevelChunk,
    SUB_CHUNK_REQUEST_MODE_LIMITED,
    SUB_CHUNK_REQUEST_MODE_LIMITLESS,
)
from mcbe.proto.packet.move_player import MovePlayer
from mcbe.proto.packet.play_status import PlayStatus, STATUS_PLAYER_SPAWN
from mcbe.proto.packet.sub_chunk import SubChunk
from mcbe.proto.pool import Packet, UnknownPacket
from mcbe.raknet import RakNetNetwork

logger = logging.getLogger(__name__)

EXAMPLES_DIR = Path(__file__).parent
HTML_PATH = EXAMPLES_DIR / "map.html"
CACHE_DIR = EXAMPLES_DIR / ".map_cache"

def _build_hash_table_from_names(block_names: list[str]) -> dict[int, str]:
    """Build hash → block name table from a list of block names (empty states)."""
    table: dict[int, str] = {}
    for name in block_names:
        if not name.startswith("minecraft:"):
            name = f"minecraft:{name}"
        h = compute_block_hash(name)
        table[h] = name
    return table

# ── カラーフォールバック ─────────────────────────────────────────

FALLBACK_COLORS: dict[str, list[int] | None] = {
    "minecraft:air": None,
    "minecraft:stone": [125, 125, 125],
    "minecraft:granite": [153, 114, 99],
    "minecraft:diorite": [188, 182, 179],
    "minecraft:andesite": [136, 136, 136],
    "minecraft:grass_block": [91, 153, 48],
    "minecraft:grass": [91, 153, 48],
    "minecraft:tallgrass": [91, 153, 48],
    "minecraft:dirt": [134, 96, 67],
    "minecraft:coarse_dirt": [119, 85, 59],
    "minecraft:cobblestone": [127, 127, 127],
    "minecraft:oak_planks": [162, 131, 78],
    "minecraft:planks": [162, 131, 78],
    "minecraft:spruce_planks": [114, 84, 48],
    "minecraft:birch_planks": [196, 179, 123],
    "minecraft:bedrock": [85, 85, 85],
    "minecraft:water": [64, 64, 255],
    "minecraft:flowing_water": [64, 64, 255],
    "minecraft:lava": [207, 92, 15],
    "minecraft:flowing_lava": [207, 92, 15],
    "minecraft:sand": [219, 207, 163],
    "minecraft:red_sand": [190, 102, 33],
    "minecraft:gravel": [136, 126, 126],
    "minecraft:gold_ore": [143, 140, 125],
    "minecraft:iron_ore": [136, 130, 127],
    "minecraft:coal_ore": [115, 115, 115],
    "minecraft:oak_log": [101, 80, 47],
    "minecraft:log": [101, 80, 47],
    "minecraft:spruce_log": [58, 37, 16],
    "minecraft:birch_log": [216, 215, 210],
    "minecraft:oak_leaves": [54, 122, 25],
    "minecraft:leaves": [54, 122, 25],
    "minecraft:spruce_leaves": [40, 73, 40],
    "minecraft:birch_leaves": [80, 132, 48],
    "minecraft:jungle_leaves": [48, 122, 19],
    "minecraft:acacia_leaves": [76, 116, 34],
    "minecraft:dark_oak_leaves": [54, 122, 25],
    "minecraft:mangrove_leaves": [57, 122, 20],
    "minecraft:azalea_leaves": [87, 120, 45],
    "minecraft:azalea_leaves_flowered": [87, 120, 45],
    "minecraft:leaves": [54, 122, 25],
    "minecraft:leaves2": [54, 122, 25],
    "minecraft:short_grass": [91, 153, 48],
    "minecraft:tall_grass": [91, 153, 48],
    "minecraft:fern": [78, 137, 41],
    "minecraft:large_fern": [78, 137, 41],
    "minecraft:vine": [54, 122, 25],
    "minecraft:lily_pad": [32, 128, 48],
    "minecraft:sponge": [195, 192, 74],
    "minecraft:glass": [175, 213, 220],
    "minecraft:lapis_ore": [99, 110, 140],
    "minecraft:lapis_block": [30, 67, 140],
    "minecraft:sandstone": [218, 210, 158],
    "minecraft:wool": [234, 234, 234],
    "minecraft:gold_block": [246, 208, 61],
    "minecraft:iron_block": [220, 220, 220],
    "minecraft:brick_block": [150, 97, 83],
    "minecraft:tnt": [219, 68, 26],
    "minecraft:mossy_cobblestone": [110, 138, 110],
    "minecraft:obsidian": [20, 18, 30],
    "minecraft:diamond_ore": [129, 140, 143],
    "minecraft:diamond_block": [97, 219, 213],
    "minecraft:redstone_ore": [133, 107, 107],
    "minecraft:redstone_block": [171, 27, 7],
    "minecraft:ice": [145, 183, 253],
    "minecraft:snow": [249, 254, 254],
    "minecraft:snow_layer": [249, 254, 254],
    "minecraft:clay": [160, 166, 179],
    "minecraft:pumpkin": [198, 118, 24],
    "minecraft:netherrack": [111, 54, 53],
    "minecraft:soul_sand": [81, 62, 50],
    "minecraft:glowstone": [171, 131, 70],
    "minecraft:mycelium": [111, 99, 107],
    "minecraft:end_stone": [219, 223, 158],
    "minecraft:emerald_ore": [108, 136, 115],
    "minecraft:emerald_block": [42, 176, 66],
    "minecraft:quartz_block": [236, 230, 223],
    "minecraft:prismarine": [99, 171, 158],
    "minecraft:hardened_clay": [150, 93, 67],
    "minecraft:stained_hardened_clay": [150, 93, 67],
    "minecraft:terracotta": [150, 93, 67],
    "minecraft:packed_ice": [141, 180, 250],
    "minecraft:blue_ice": [116, 167, 253],
    "minecraft:concrete": [207, 213, 214],
    "minecraft:concrete_powder": [225, 227, 228],
    "minecraft:deepslate": [80, 80, 82],
    "minecraft:cobbled_deepslate": [77, 77, 80],
    "minecraft:tuff": [108, 109, 102],
    "minecraft:calcite": [224, 224, 219],
    "minecraft:dripstone_block": [134, 107, 92],
    "minecraft:copper_ore": [124, 125, 120],
    "minecraft:copper_block": [192, 107, 79],
    "minecraft:amethyst_block": [133, 97, 168],
    "minecraft:moss_block": [89, 109, 45],
    "minecraft:mud": [60, 57, 55],
    "minecraft:mangrove_log": [84, 68, 44],
    "minecraft:mangrove_leaves": [57, 122, 20],
    "minecraft:cherry_log": [53, 25, 34],
    "minecraft:cherry_leaves": [229, 164, 185],
    "minecraft:bamboo_block": [175, 169, 73],
    "minecraft:crimson_nylium": [130, 31, 31],
    "minecraft:warped_nylium": [43, 114, 101],
    "minecraft:basalt": [73, 72, 77],
    "minecraft:blackstone": [42, 36, 40],
    "minecraft:nether_bricks": [44, 22, 26],
    "minecraft:ancient_debris": [101, 73, 63],
    "minecraft:sculk": [12, 28, 35],
    "minecraft:podzol": [91, 63, 24],
    "minecraft:farmland": [110, 76, 49],
    "minecraft:grass_path": [148, 121, 65],
    "minecraft:oak_fence": [162, 131, 78],
    "minecraft:oak_stairs": [162, 131, 78],
    "minecraft:stone_stairs": [125, 125, 125],
    "minecraft:cobblestone_wall": [127, 127, 127],
    "minecraft:stone_slab": [125, 125, 125],
    "minecraft:wooden_slab": [162, 131, 78],
    "minecraft:double_stone_slab": [125, 125, 125],
}


def _load_jsonc(path: Path) -> dict:
    """Load a JSON file that may contain // comments."""
    import re
    text = path.read_text(encoding="utf-8")
    # Remove single-line // comments (but not inside strings).
    text = re.sub(r'(?<!["\w])//[^\n]*', '', text)
    return json.loads(text)


def _iter_block_textures(rp_path: Path):
    """Yield ``(block_name, img_path)`` for blocks with a resolvable top-face texture.

    *block_name* is the bare name (e.g. ``"stone"``), *img_path* is the
    absolute path to the source image file (.png or .tga).
    """
    blocks_json = rp_path / "blocks.json"
    terrain_json = rp_path / "textures" / "terrain_texture.json"
    if not blocks_json.exists() or not terrain_json.exists():
        return

    blocks = _load_jsonc(blocks_json)
    terrain = _load_jsonc(terrain_json)
    texture_data = terrain.get("texture_data", {})

    for block_name, block_info in blocks.items():
        if not isinstance(block_info, dict):
            continue
        tex = block_info.get("textures")
        if tex is None:
            continue

        # Resolve texture name: can be string, dict with face keys, or nested.
        tex_name = None
        if isinstance(tex, str):
            tex_name = tex
        elif isinstance(tex, dict):
            # Prefer "up" face for top-down view, then "side", then any.
            for key in ("up", "side", "north", "down"):
                if key in tex:
                    v = tex[key]
                    tex_name = v if isinstance(v, str) else v.get("texture") if isinstance(v, dict) else None
                    if tex_name:
                        break
            if not tex_name:
                for v in tex.values():
                    if isinstance(v, str):
                        tex_name = v
                        break

        if not tex_name or tex_name not in texture_data:
            continue

        td = texture_data[tex_name]
        textures = td.get("textures")
        if textures is None:
            continue

        # Resolve file path: collect all candidates to try.
        file_paths: list[str] = []
        if isinstance(textures, str):
            file_paths.append(textures)
        elif isinstance(textures, dict):
            p = textures.get("path")
            if p:
                file_paths.append(p)
        elif isinstance(textures, list):
            for entry in textures:
                if isinstance(entry, str):
                    file_paths.append(entry)
                elif isinstance(entry, dict):
                    p = entry.get("path")
                    if p:
                        file_paths.append(p)

        # Deduplicate while preserving order.
        seen_paths: set[str] = set()
        unique_paths: list[str] = []
        for p in file_paths:
            if p not in seen_paths:
                seen_paths.add(p)
                unique_paths.append(p)

        for candidate in unique_paths:
            img_path = _resolve_texture_path(rp_path, candidate)
            if img_path is not None:
                yield block_name, img_path
                break


def _generate_colors_from_resource_pack(rp_path: Path) -> dict[str, list[int] | None]:
    """Generate block color table from a resource pack directory."""
    colors: dict[str, list[int] | None] = {"minecraft:air": None}
    for block_name, img_path in _iter_block_textures(rp_path):
        try:
            avg = _average_png_color(img_path)
            if avg:
                colors[f"minecraft:{block_name}"] = avg
        except Exception:
            pass
    return colors


# Blocks whose textures are greyscale and tinted at runtime.
# Tint color = default biome appearance (plains-like).
_TINT_MAP: dict[str, tuple[int, int, int]] = {
    # grass / ground cover
    "grass": (91, 153, 48),
    "tallgrass": (91, 153, 48),
    "short_grass": (91, 153, 48),
    "tall_grass": (91, 153, 48),
    "fern": (78, 137, 41),
    "large_fern": (78, 137, 41),
    "double_plant": (91, 153, 48),
    "vine": (54, 122, 25),
    "lily_pad": (32, 128, 48),
    # leaves
    "oak_leaves": (54, 122, 25),
    "leaves": (54, 122, 25),
    "leaves2": (54, 122, 25),
    "spruce_leaves": (40, 73, 40),
    "birch_leaves": (80, 132, 48),
    "jungle_leaves": (48, 122, 19),
    "acacia_leaves": (76, 116, 34),
    "dark_oak_leaves": (54, 122, 25),
    "mangrove_leaves": (57, 122, 20),
    "azalea_leaves": (87, 120, 45),
    "azalea_leaves_flowered": (87, 120, 45),
    # water
    "water": (64, 64, 255),
    "flowing_water": (64, 64, 255),
}


def _save_texture(src_path: Path, dst: Path, tint: tuple[int, int, int] | None) -> None:
    """Save a block texture to *dst*, optionally applying a tint."""
    from PIL import Image

    img = Image.open(src_path).convert("RGBA")
    if tint is not None:
        # Multiply greyscale luminance by tint colour.
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                grey = (r + g + b) // 3
                pixels[x, y] = (
                    grey * tint[0] // 255,
                    grey * tint[1] // 255,
                    grey * tint[2] // 255,
                    a,
                )
    img.save(dst, "PNG")


def _cache_block_textures(rp_path: Path) -> None:
    """Copy top-face block textures to ``.map_cache/textures/``.

    Each block is saved as ``<block_name>.png`` (e.g. ``stone.png``).
    Greyscale tinted blocks (grass, leaves, water …) are coloured with a
    default biome tint.  Files that already exist are skipped.
    """
    dest_dir = CACHE_DIR / "textures"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0
    for block_name, src_path in _iter_block_textures(rp_path):
        dst = dest_dir / f"{block_name}.png"
        if dst.exists():
            skipped += 1
            continue
        try:
            tint = _TINT_MAP.get(block_name)
            if tint is not None or src_path.suffix.lower() != ".png":
                _save_texture(src_path, dst, tint)
            else:
                import shutil
                shutil.copy2(src_path, dst)
            copied += 1
        except Exception as e:
            logger.debug("テクスチャコピー失敗 %s: %s", block_name, e)
    logger.info("テクスチャキャッシュ: %d コピー, %d スキップ (%s)", copied, skipped, dest_dir)


def _build_texture_atlas() -> tuple[bytes | None, dict]:
    """Build a texture atlas PNG and mapping from cached block textures.

    Returns ``(atlas_png_bytes, mapping_dict)``.  The mapping contains
    ``tile_size``, ``columns``, and ``blocks: {name: [col, row]}``.
    Results are cached to disk so PIL is only needed on first run.
    """
    tex_dir = CACHE_DIR / "textures"
    atlas_cache = CACHE_DIR / "texture_atlas.png"
    mapping_cache = CACHE_DIR / "texture_atlas.json"

    # Return disk cache if available.
    if atlas_cache.exists() and mapping_cache.exists():
        try:
            atlas_bytes = atlas_cache.read_bytes()
            with open(mapping_cache) as f:
                mapping = json.load(f)
            logger.info(
                "テクスチャアトラス: キャッシュから読み込み (%d ブロック)",
                len(mapping.get("blocks", {})),
            )
            return atlas_bytes, mapping
        except Exception:
            pass

    if not tex_dir.exists():
        return None, {}

    try:
        from PIL import Image
    except ImportError:
        logger.warning("PIL が利用できないためテクスチャアトラスは無効")
        return None, {}

    textures = sorted(tex_dir.glob("*.png"))
    if not textures:
        return None, {}

    TILE = 16
    COLS = 48
    rows_needed = (len(textures) + COLS - 1) // COLS

    atlas = Image.new("RGBA", (COLS * TILE, rows_needed * TILE), (0, 0, 0, 0))
    blocks_mapping: dict[str, list[int]] = {}

    for i, tex_path in enumerate(textures):
        col = i % COLS
        row = i // COLS
        try:
            img = Image.open(tex_path).convert("RGBA")
            if img.size != (TILE, TILE):
                img = img.resize((TILE, TILE), Image.NEAREST)
            atlas.paste(img, (col * TILE, row * TILE))
            blocks_mapping[f"minecraft:{tex_path.stem}"] = [col, row]
        except Exception as e:
            logger.debug("テクスチャ読み込み失敗 %s: %s", tex_path.stem, e)

    # Add aliases for protocol names that differ from blocks.json keys.
    _BLOCK_RENAMES: dict[str, str] = {
        "grass_block": "grass",
        "sea_lantern": "seaLantern",
        "concrete_powder": "concretePowder",
        "invisible_bedrock": "invisibleBedrock",
        "moving_block": "movingBlock",
        "piston_arm_collision": "pistonArmCollision",
        "sticky_piston_arm_collision": "stickyPistonArmCollision",
        "trip_wire": "tripWire",
    }
    for proto_name, tex_name in _BLOCK_RENAMES.items():
        key = f"minecraft:{proto_name}"
        src = f"minecraft:{tex_name}"
        if key not in blocks_mapping and src in blocks_mapping:
            blocks_mapping[key] = blocks_mapping[src]

    from io import BytesIO as _BytesIO

    buf = _BytesIO()
    atlas.save(buf, "PNG")
    atlas_bytes = buf.getvalue()

    mapping = {
        "tile_size": TILE,
        "columns": COLS,
        "blocks": blocks_mapping,
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    atlas_cache.write_bytes(atlas_bytes)
    with open(mapping_cache, "w") as f:
        json.dump(mapping, f)

    logger.info(
        "テクスチャアトラス生成: %d ブロック (%dx%d)",
        len(blocks_mapping),
        COLS * TILE,
        rows_needed * TILE,
    )
    return atlas_bytes, mapping


def _resolve_texture_path(rp_path: Path, file_path: str) -> Path | None:
    """Resolve a texture file path, trying .png and .tga extensions."""
    for ext in (".png", ".tga"):
        p = rp_path / (file_path + ext)
        if p.exists():
            return p
    # Try without extension (file may already have one).
    p = rp_path / file_path
    if p.exists():
        return p
    return None


def _average_png_color(path: Path) -> list[int] | None:
    """Compute average RGB from an image file (PNG or TGA)."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        pixels = list(img.tobytes())
        # tobytes returns flat RGBA bytes; reshape into tuples of 4
        pixels = [
            (pixels[i], pixels[i+1], pixels[i+2], pixels[i+3])
            for i in range(0, len(pixels), 4)
        ]
        if not pixels:
            return None
        r_sum = g_sum = b_sum = 0
        count = 0
        for r, g, b, a in pixels:
            if a < 128:
                continue
            r_sum += r
            g_sum += g
            b_sum += b
            count += 1
        if count == 0:
            return None
        return [r_sum // count, g_sum // count, b_sum // count]
    except ImportError:
        return None


def load_block_colors(
    resource_pack: str | None = None,
    state: MapState | None = None,
) -> dict[str, list[int] | None]:
    """Load or generate block color table.

    If *state* is provided, also builds the FNV-1a hash → block name table
    from the blocks.json found alongside the resource pack.
    """
    cache_path = CACHE_DIR / "block_colors.json"

    # Detect resource pack paths (used for both colors and texture cache).
    rp_paths: list[Path] = []
    if resource_pack:
        rp_paths.append(Path(resource_pack))
    for candidate in [
        EXAMPLES_DIR.parent.parent / "bedrock-samples" / "resource_pack",
        EXAMPLES_DIR.parent / "bedrock-samples" / "resource_pack",
    ]:
        if candidate.exists():
            rp_paths.append(candidate)

    # Cache block textures (skips files that already exist).
    for rp in rp_paths:
        _cache_block_textures(rp)
        break  # one resource pack is enough

    # 1. Cached colors.
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                colors = json.load(f)
            logger.info("カラーテーブルをキャッシュから読み込み: %d ブロック", len(colors))
            if state is not None:
                _init_hash_table(state, colors)
            return colors
        except Exception:
            pass

    # 2. Generate from resource pack.
    for rp in rp_paths:
        colors = _generate_colors_from_resource_pack(rp)
        if colors and len(colors) > 10:
            merged = dict(colors)
            merged.update(FALLBACK_COLORS)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(merged, f)
            logger.info("カラーテーブルを生成: %d ブロック (%s)", len(merged), rp)
            if state is not None:
                _init_hash_table(state, merged)
            return merged

    # 3. Fallback.
    logger.info("フォールバックカラーテーブルを使用: %d ブロック", len(FALLBACK_COLORS))
    if state is not None:
        _init_hash_table(state, FALLBACK_COLORS)
    return dict(FALLBACK_COLORS)


def _init_hash_table(state: MapState, colors: dict[str, list[int] | None]) -> None:
    """Pre-load canonical block state hashes.

    The canonical hash table covers all vanilla block states with correct
    NBT types, ensuring proper hash resolution for Realms and BDS servers.
    """
    canonical = load_canonical_block_hashes()
    state.hash_table.update(canonical)
    logger.info("初期ハッシュテーブル: %d エントリ (canonical block states)", len(state.hash_table))


# ── ログ設定 ─────────────────────────────────────────────────────


class _ColorFormatter(logging.Formatter):
    _COLORS = {
        logging.DEBUG: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[31m",
    }
    _RESET = "\033[0m"

    def format(self, record):
        msg = super().format(record)
        color = self._COLORS.get(record.levelno)
        return f"{color}{msg}{self._RESET}" if color else msg


def _setup_logging(level: int) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_ColorFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)
    logging.getLogger(__name__).setLevel(min(level, logging.INFO))


# ── MapState ─────────────────────────────────────────────────────


@dataclass
class PlayerInfo:
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0


@dataclass
class MapState:
    block_palette: list[str] = field(default_factory=list)
    use_hashes: bool = False
    hash_table: dict[int, str] = field(default_factory=dict)
    chunks: dict[tuple[int, int], list[str]] = field(default_factory=dict)
    chunk_top_y: dict[tuple[int, int], list[int]] = field(default_factory=dict)
    players: dict[int, PlayerInfo] = field(default_factory=dict)
    bot_entity_id: int = 0
    world_name: str = ""
    world_seed: int = 0
    dirty_chunks: set[tuple[int, int]] = field(default_factory=set)
    cache_dir: Path | None = None

    def save_chunk(self, cx: int, cz: int) -> None:
        """Save a chunk to disk cache."""
        if self.cache_dir is None or (cx, cz) not in self.chunks:
            return
        chunks_dir = self.cache_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        top_blocks = self.chunks[(cx, cz)]

        # Build local palette for compact storage.
        palette_set = sorted(set(top_blocks))
        palette_map = {name: i for i, name in enumerate(palette_set)}
        grid = bytes(palette_map[name] for name in top_blocks)

        data = json.dumps(palette_set).encode() + b"\n" + grid
        (chunks_dir / f"{cx}_{cz}.bin").write_bytes(data)

    def load_cache(self) -> None:
        """Load cached chunks from disk and mark them dirty for broadcast."""
        if self.cache_dir is None:
            return
        chunks_dir = self.cache_dir / "chunks"
        if not chunks_dir.exists():
            return
        count = 0
        for f in chunks_dir.glob("*.bin"):
            try:
                parts = f.stem.split("_")
                cx, cz = int(parts[0]), int(parts[1])
                raw = f.read_bytes()
                newline = raw.index(b"\n")
                palette = json.loads(raw[:newline])
                grid = raw[newline + 1:]
                if len(grid) == 256:
                    self.chunks[(cx, cz)] = [palette[b] for b in grid]
                    # Cached data is stale; low Y lets live sub-chunks
                    # overwrite it.  Higher sub-chunks will then overwrite
                    # lower ones via the Y tracking in _handle_sub_chunk.
                    self.chunk_top_y[(cx, cz)] = [-9999] * 256
                    self.dirty_chunks.add((cx, cz))
                    count += 1
            except Exception:
                continue
        if count:
            logger.info("キャッシュから %d チャンクを復元", count)

    def save_palette(self) -> None:
        if self.cache_dir is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_dir / "palette.json", "w") as f:
            json.dump(self.block_palette, f)

    def load_palette(self) -> bool:
        if self.cache_dir is None:
            return False
        p = self.cache_dir / "palette.json"
        if not p.exists():
            return False
        try:
            with open(p) as f:
                self.block_palette = json.load(f)
            return True
        except Exception:
            return False


# ── MapDialer ────────────────────────────────────────────────────


class MapDialer(Dialer):
    """Dialer that captures StartGame data for map rendering."""

    def __init__(self, *args, map_state: MapState, **kwargs):
        super().__init__(*args, **kwargs)
        self._map_state = map_state

    async def _wait_for_spawn(self, conn: Connection) -> None:
        from mcbe.proto.packet.disconnect import Disconnect
        from mcbe.proto.packet.packet_violation_warning import PacketViolationWarning
        from mcbe.proto.packet.start_game import StartGame
        from mcbe.proto.packet.chunk_radius_updated import ChunkRadiusUpdated
        from mcbe.proto.packet.request_chunk_radius import RequestChunkRadius

        # StartGame is not in the default server pool — register it so
        # conn.read_packet() deserializes it instead of returning UnknownPacket.
        conn._pool[StartGame.packet_id] = StartGame

        chunk_radius_sent = False

        while True:
            pk = await asyncio.wait_for(conn.read_packet(), timeout=30.0)
            logger.debug("spawn: received %s (id=%d)", type(pk).__name__, pk.packet_id)

            if isinstance(pk, Disconnect):
                logger.error("spawn: Disconnect reason=%d message=%s", pk.reason, pk.message)
                raise ConnectionError(f"server disconnected: {pk.message}")

            if isinstance(pk, PacketViolationWarning):
                logger.error("spawn: PacketViolationWarning type=%d severity=%d packet=%d ctx=%s",
                             pk.violation_type, pk.severity, pk.violating_packet_id, pk.violation_context)

            if isinstance(pk, StartGame):
                state = self._map_state
                state.block_palette = [e.name for e in pk.blocks]
                state.use_hashes = pk.use_block_network_id_hashes
                state.bot_entity_id = pk.entity_runtime_id
                state.world_name = pk.world_name
                state.world_seed = pk.world_seed
                state.players[pk.entity_runtime_id] = PlayerInfo(
                    name="bot", x=pk.player_position.x,
                    y=pk.player_position.y, z=pk.player_position.z,
                )

                # Build hash table from canonical block states.
                if state.use_hashes:
                    canonical = load_canonical_block_hashes()
                    state.hash_table.update(canonical)
                    # Also add any custom block entries from StartGame.
                    for entry in pk.blocks:
                        if entry.properties_typed is not None:
                            h = compute_block_hash_typed(entry.name, entry.properties_typed)
                        else:
                            h = compute_block_hash(entry.name, entry.properties)
                        state.hash_table[h] = entry.name
                    logger.info(
                        "ハッシュテーブル: canonical=%d + StartGame=%d → %d エントリ",
                        len(canonical), len(pk.blocks), len(state.hash_table),
                    )

                logger.info("StartGame: world=%s blocks=%d entity_id=%d hashes=%s",
                            pk.world_name, len(state.block_palette),
                            pk.entity_runtime_id, pk.use_block_network_id_hashes)

                # Setup cache directory.
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in pk.world_name)
                state.cache_dir = CACHE_DIR / f"{safe_name}_{pk.world_seed}"
                state.save_palette()
                state.load_cache()

            if isinstance(pk, PlayStatus):
                logger.info("spawn: PlayStatus=%d", pk.status)
                if pk.status == STATUS_PLAYER_SPAWN:
                    break

            elif isinstance(pk, ChunkRadiusUpdated):
                logger.info("spawn: ChunkRadiusUpdated=%d", pk.chunk_radius)

            elif isinstance(pk, LevelChunk):
                need_req = self._handle_level_chunk(pk)
                if need_req:
                    await self._send_sub_chunk_request(conn, *need_req)

            elif isinstance(pk, SubChunk):
                self._handle_sub_chunk(pk)

            if not chunk_radius_sent:
                await conn.write_packet(
                    RequestChunkRadius(
                        chunk_radius=self.chunk_radius,
                        max_chunk_radius=self.chunk_radius,
                    )
                )
                await conn.flush()
                chunk_radius_sent = True

    def _handle_level_chunk(self, pk: LevelChunk) -> tuple[int, int, int, int] | None:
        return _handle_level_chunk(pk, self._map_state)

    def _handle_sub_chunk(self, pk: SubChunk) -> None:
        _handle_sub_chunk(pk, self._map_state)

    async def _send_sub_chunk_request(
        self, conn: Connection, cx: int, cz: int, dim: int, highest: int,
    ) -> None:
        await _send_sub_chunk_request(conn, cx, cz, dim, highest)


# ── Packet handlers ──────────────────────────────────────────────


def _handle_level_chunk(
    pk: LevelChunk, state: MapState,
) -> tuple[int, int, int, int] | None:
    """Process a LevelChunk packet.

    Returns ``(cx, cz, dimension, highest_sub_chunk)`` when the chunk uses
    sub-chunk request mode and a SubChunkRequest should be sent.
    """
    cx, cz = pk.position.x, pk.position.z
    sc = pk.sub_chunk_count

    if sc >= SUB_CHUNK_REQUEST_MODE_LIMITED:
        return (cx, cz, pk.dimension, pk.highest_sub_chunk)

    try:
        ht = state.hash_table if state.use_hashes else None
        top = parse_level_chunk_top_blocks(pk.raw_payload, sc, state.block_palette, ht)
        if top:
            state.chunks[(cx, cz)] = top
            state.dirty_chunks.add((cx, cz))
            state.save_chunk(cx, cz)
            non_air = sum(1 for b in top if b != AIR)
            if len(state.chunks) <= 5 or len(state.chunks) % 50 == 0:
                logger.info("LevelChunk (%d,%d) sc=%d non_air=%d total=%d",
                            cx, cz, sc, non_air, len(state.chunks))
    except Exception as e:
        logger.debug("LevelChunk parse error at (%d,%d): %s", cx, cz, e)
    return None


async def _send_sub_chunk_request(
    conn: Connection, cx: int, cz: int, dim: int, highest: int,
) -> None:
    """Send a SubChunkRequest for all Y levels of a chunk."""
    from mcbe.proto.packet.sub_chunk_request import SubChunkRequest, SubChunkOffset
    from mcbe.proto.types import SubChunkPos

    min_y = -4  # sub-chunk Y = -4 corresponds to block Y = -64
    offsets = [SubChunkOffset(x=0, y=y, z=0) for y in range(min_y, highest + 1)]
    try:
        await conn.write_packet(SubChunkRequest(
            dimension=dim,
            position=SubChunkPos(x=cx, y=0, z=cz),
            offsets=offsets,
        ))
        await conn.flush()
    except Exception as e:
        logger.debug("SubChunkRequest send error: %s", e)


_sub_chunk_count = 0  # diagnostic counter


def _handle_sub_chunk(pk: SubChunk, state: MapState) -> None:
    """Process a SubChunk packet."""
    global _sub_chunk_count
    ht = state.hash_table if state.use_hashes else None
    try:
        entries = parse_sub_chunk_entries(pk.sub_chunk_entries, pk.cache_enabled, ht)
    except Exception as e:
        logger.debug("SubChunk parse error: %s", e)
        return

    base_x = pk.position.x
    base_z = pk.position.z

    _sub_chunk_count += 1

    for (ox, oy, oz), ids, local_palette, rc in entries:
        if ids is None:
            continue
        chunk_x = base_x + ox
        chunk_z = base_z + oz

        key = (chunk_x, chunk_z)
        if key not in state.chunks:
            state.chunks[key] = [AIR] * 256
            state.chunk_top_y[key] = [-9999] * 256

        # When hash_table is provided, chunk.py resolves hashes internally
        # and always returns a local_palette.  Otherwise fall back to global.
        if local_palette is not None:
            pal = local_palette
            pal_len = len(pal)
        else:
            pal = state.block_palette
            pal_len = len(pal)

        existing = state.chunks[key]
        top_y = state.chunk_top_y[key]
        base_block_y = oy * 16
        for x in range(16):
            for z in range(16):
                col = x * 16 + z
                for y in range(15, -1, -1):
                    rid = ids[(x << 8) | (z << 4) | y]
                    name = pal[rid] if rid < pal_len else AIR
                    if name != AIR:
                        abs_y = base_block_y + y
                        if abs_y >= top_y[col]:
                            existing[col] = name
                            top_y[col] = abs_y
                        break

        state.dirty_chunks.add(key)
        state.save_chunk(chunk_x, chunk_z)


# ── Web server ───────────────────────────────────────────────────


async def serve_html(request: web.Request) -> web.Response:
    if HTML_PATH.exists():
        return web.Response(text=HTML_PATH.read_text(), content_type="text/html")
    return web.Response(text="map.html not found", status=404)


async def serve_block_colors(request: web.Request) -> web.Response:
    colors = request.app["block_colors"]
    return web.json_response(colors)


async def serve_texture_atlas(request: web.Request) -> web.Response:
    atlas_bytes = request.app.get("texture_atlas")
    if atlas_bytes is None:
        return web.Response(status=404)
    return web.Response(body=atlas_bytes, content_type="image/png")


async def serve_texture_mapping(request: web.Request) -> web.Response:
    mapping = request.app.get("texture_mapping", {})
    return web.json_response(mapping)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients: set[web.WebSocketResponse] = request.app["ws_clients"]
    state: MapState = request.app["state"]
    ws_clients.add(ws)
    logger.info("WebSocket クライアント接続 (合計 %d)", len(ws_clients))

    # Send init with all cached chunks.
    try:
        chunks_data = _build_all_chunks(state)
        players_data = _build_players(state)
        await ws.send_str(json.dumps({
            "type": "init",
            "players": players_data,
            "chunks": chunks_data,
        }))
    except Exception as e:
        logger.warning("init send error: %s", e)

    try:
        async for msg in ws:
            pass  # No client messages expected.
    except Exception:
        pass
    finally:
        ws_clients.discard(ws)
        logger.info("WebSocket クライアント切断 (残り %d)", len(ws_clients))

    return ws


def _build_chunk_data(cx: int, cz: int, top_blocks: list[str]) -> dict:
    """Build a compact chunk data dict for WebSocket."""
    palette_set = sorted(set(top_blocks))
    palette_map = {name: i for i, name in enumerate(palette_set)}
    grid = bytes(palette_map[name] for name in top_blocks)
    return {
        "cx": cx, "cz": cz,
        "palette": palette_set,
        "data": base64.b64encode(grid).decode(),
    }


def _build_all_chunks(state: MapState) -> list[dict]:
    chunks = []
    for (cx, cz), top_blocks in state.chunks.items():
        chunks.append(_build_chunk_data(cx, cz, top_blocks))
    return chunks


def _build_players(state: MapState) -> list[dict]:
    return [
        {"name": p.name, "x": p.x, "z": p.z, "yaw": p.yaw}
        for p in state.players.values()
    ]


async def ws_broadcast_loop(state: MapState, ws_clients: set[web.WebSocketResponse]) -> None:
    """Broadcast dirty chunks and player positions to all WebSocket clients."""
    while True:
        await asyncio.sleep(0.1)
        if not ws_clients:
            continue

        dirty = state.dirty_chunks.copy()
        state.dirty_chunks.clear()

        chunks_data = []
        for cx, cz in dirty:
            top_blocks = state.chunks.get((cx, cz))
            if top_blocks:
                chunks_data.append(_build_chunk_data(cx, cz, top_blocks))

        msg = json.dumps({
            "type": "update",
            "players": _build_players(state),
            "chunks": chunks_data,
        })

        dead: set[web.WebSocketResponse] = set()
        for ws in ws_clients:
            try:
                await ws.send_str(msg)
            except Exception:
                dead.add(ws)
        ws_clients -= dead


async def start_web_server(
    state: MapState,
    block_colors: dict,
    ws_clients: set[web.WebSocketResponse],
    port: int,
) -> tuple[web.AppRunner, asyncio.Task]:
    atlas_bytes, texture_mapping = _build_texture_atlas()

    app = web.Application()
    app["state"] = state
    app["block_colors"] = block_colors
    app["ws_clients"] = ws_clients
    app["texture_atlas"] = atlas_bytes
    app["texture_mapping"] = texture_mapping

    app.router.add_get("/", serve_html)
    app.router.add_get("/block_colors.json", serve_block_colors)
    app.router.add_get("/texture_atlas.png", serve_texture_atlas)
    app.router.add_get("/texture_atlas.json", serve_texture_mapping)
    app.router.add_get("/ws", websocket_handler)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Map viewer: http://localhost:%d", port)

    broadcast_task = asyncio.create_task(ws_broadcast_loop(state, ws_clients))
    return runner, broadcast_task


# ── 単独モード ───────────────────────────────────────────────────


async def run_standalone(
    address: str,
    state: MapState,
    block_colors: dict,
    web_port: int,
    realms: bool = False,
    invite_code: str | None = None,
    backend: str | None = None,
) -> None:
    ws_clients: set[web.WebSocketResponse] = set()
    runner, broadcast_task = await start_web_server(state, block_colors, ws_clients, web_port)

    login_chain = None
    auth_key = None
    multiplayer_token = ""
    network = None

    if realms:
        address, login_chain, auth_key, multiplayer_token, network = await _resolve_realms(
            invite_code, backend=backend,
        )
    if network is None:
        network = RakNetNetwork()

    dialer = MapDialer(
        identity_data=IdentityData(display_name="map_bot"),
        network=network,
        login_chain=login_chain,
        auth_key=auth_key,
        multiplayer_token=multiplayer_token,
        map_state=state,
    )

    try:
        conn = await dialer.dial(address)
    except Exception as e:
        logger.error("接続失敗: %s", e)
        broadcast_task.cancel()
        await runner.cleanup()
        return

    logger.info("接続完了 — チャンク受信中")

    try:
        recv_task = asyncio.create_task(_recv_loop(conn, state))
        tp_task = asyncio.create_task(_teleport_loop(conn, state))
        await asyncio.gather(recv_task, tp_task)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.info("切断: %s", e)
    finally:
        await conn.close()
        broadcast_task.cancel()
        await runner.cleanup()


async def _recv_loop(conn: Connection, state: MapState) -> None:
    """Receive and process packets from the server."""
    while not conn.closed:
        try:
            pk = await conn.read_packet()
        except Exception:
            break

        if isinstance(pk, LevelChunk):
            need_request = _handle_level_chunk(pk, state)
            if need_request:
                await _send_sub_chunk_request(conn, *need_request)
        elif isinstance(pk, SubChunk):
            _handle_sub_chunk(pk, state)
        elif isinstance(pk, MovePlayer):
            eid = pk.entity_runtime_id
            if eid in state.players:
                p = state.players[eid]
                p.x = pk.position.x
                p.y = pk.position.y
                p.z = pk.position.z
                p.yaw = pk.yaw
            elif eid == state.bot_entity_id:
                state.players[eid] = PlayerInfo(
                    name="bot", x=pk.position.x, y=pk.position.y,
                    z=pk.position.z, yaw=pk.yaw,
                )
        elif isinstance(pk, CommandOutput):
            # querytarget response handling.
            if pk.data_set:
                _handle_querytarget(pk.data_set, state)


async def _teleport_loop(conn: Connection, state: MapState) -> None:
    """Periodically query player positions and teleport to cover all areas."""
    await asyncio.sleep(3.0)  # Wait for initial chunks.

    last_tp_target: tuple[float, float] | None = None

    while not conn.closed:
        # Collect other players' positions (exclude bot).
        other_players = [
            p for eid, p in state.players.items()
            if eid != state.bot_entity_id and p.name != "bot"
        ]

        if other_players:
            # Teleport to the first non-bot player's position.
            target = other_players[0]
            tp_x, tp_z = target.x, target.z
        else:
            # No other players — default to (0, 0).
            tp_x, tp_z = 0.0, 0.0

        # Only teleport if target changed significantly.
        if last_tp_target is None or (
            abs(tp_x - last_tp_target[0]) > 16 or abs(tp_z - last_tp_target[1]) > 16
        ):
            try:
                await conn.write_packet(CommandRequest(
                    command_line=f"/tp @s {tp_x:.0f} 320 {tp_z:.0f}",
                    command_origin=CommandOrigin(
                        origin=ORIGIN_AUTOMATION_PLAYER,
                        request_id=str(_uuid.uuid4()),
                    ),
                    internal=False,
                ))
                await conn.flush()
                last_tp_target = (tp_x, tp_z)
            except Exception:
                break

        # Query all player positions.
        try:
            await conn.write_packet(CommandRequest(
                command_line="/querytarget @a",
                command_origin=CommandOrigin(
                    origin=ORIGIN_AUTOMATION_PLAYER,
                    request_id=str(_uuid.uuid4()),
                ),
                internal=False,
            ))
            await conn.flush()
        except Exception:
            break

        await asyncio.sleep(5.0)


def _handle_querytarget(data_set: str, state: MapState) -> None:
    """Parse /querytarget response and update player positions."""
    try:
        results = json.loads(data_set)
        if not isinstance(results, list):
            return
        for entry in results:
            if not isinstance(entry, dict):
                continue
            pos = entry.get("position")
            name = entry.get("uniqueId", "")
            if pos and isinstance(pos, dict):
                # Store by name as a simple player ID.
                found = False
                for p in state.players.values():
                    if p.name == name:
                        p.x = float(pos.get("x", 0))
                        p.y = float(pos.get("y", 0))
                        p.z = float(pos.get("z", 0))
                        found = True
                        break
                if not found:
                    # Add as new player (use hash of name as fake entity ID).
                    eid = hash(name) & 0xFFFFFFFF
                    state.players[eid] = PlayerInfo(
                        name=name,
                        x=float(pos.get("x", 0)),
                        y=float(pos.get("y", 0)),
                        z=float(pos.get("z", 0)),
                    )
    except (json.JSONDecodeError, ValueError):
        pass


# ── proxy モード ─────────────────────────────────────────────────


async def run_proxy(
    listen_addr: str,
    remote_addr: str,
    state: MapState,
    block_colors: dict,
    web_port: int,
) -> None:
    from mcbe.listener import ListenConfig, listen
    from mcbe.network import TCPNetwork

    ws_clients: set[web.WebSocketResponse] = set()
    runner, broadcast_task = await start_web_server(state, block_colors, ws_clients, web_port)

    network = TCPNetwork()
    config = ListenConfig(server_name="mcbe Map Proxy", authentication_disabled=True)

    logger.info("Proxy: %s → %s", listen_addr, remote_addr)
    server = await listen(listen_addr, config=config, network=network)

    try:
        while True:
            client_conn = await server.accept()
            asyncio.create_task(
                _handle_proxy_connection(client_conn, remote_addr, network, state)
            )
    except asyncio.CancelledError:
        pass
    finally:
        await server.close()
        broadcast_task.cancel()
        await runner.cleanup()


async def _handle_proxy_connection(
    client_conn: Connection,
    remote_addr: str,
    network,
    state: MapState,
) -> None:
    logger.info("Proxy: クライアント接続、リモート %s に接続中", remote_addr)

    dialer = MapDialer(
        identity_data=IdentityData(
            display_name="ProxyPlayer",
            identity="00000000-0000-0000-0000-000000000000",
        ),
        network=network,
        map_state=state,
    )

    try:
        server_conn = await dialer.dial(remote_addr)
    except Exception as e:
        logger.error("リモート接続失敗: %s", e)
        await client_conn.close()
        return

    logger.info("Proxy: リモート接続完了")

    c2s = asyncio.create_task(_forward_packets(client_conn, server_conn, "C→S", state))
    s2c = asyncio.create_task(_forward_packets(server_conn, client_conn, "S→C", state))

    done, pending = await asyncio.wait([c2s, s2c], return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    await server_conn.close()
    await client_conn.close()
    logger.info("Proxy: 接続終了")


async def _forward_packets(
    src: Connection, dst: Connection, direction: str, state: MapState,
) -> None:
    try:
        while not src.closed and not dst.closed:
            pk = await src.read_packet()

            if direction == "S→C":
                try:
                    if isinstance(pk, LevelChunk):
                        _handle_level_chunk(pk, state)
                    elif isinstance(pk, SubChunk):
                        _handle_sub_chunk(pk, state)
                    elif isinstance(pk, MovePlayer):
                        if pk.entity_runtime_id == state.bot_entity_id:
                            if state.bot_entity_id in state.players:
                                p = state.players[state.bot_entity_id]
                                p.x = pk.position.x
                                p.y = pk.position.y
                                p.z = pk.position.z
                                p.yaw = pk.yaw
                except Exception as e:
                    logger.debug("proxy intercept error: %s", e)

            await dst.write_packet(pk)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.debug("[%s] closed: %s", direction, e)


# ── Realms 認証 ──────────────────────────────────────────────────


async def _resolve_realms(invite_code: str | None = None, backend: str | None = None):
    from mcbe.auth.live import get_live_token, load_token
    from mcbe.auth.xbox import request_xbl_token
    from mcbe.auth.minecraft import request_minecraft_chain

    cached = load_token()
    live_token = await get_live_token()
    if cached and cached.valid():
        logger.info("キャッシュ済みトークンを使用")
    elif cached:
        logger.info("トークンを更新しました")
    else:
        logger.info("新規認証完了")

    from mcbe.realms import RealmsClient
    xbl_realms = await request_xbl_token(live_token, "https://pocket.realms.minecraft.net/")
    async with RealmsClient(xbl_realms) as client:
        if invite_code:
            realm = await client.realm(invite_code)
        else:
            realms = await client.realms()
            if not realms:
                raise RuntimeError("アクセス可能な Realm がありません")
            realm = realms[0]
        logger.info("Realm: %s (%s)", realm.name, realm.state)
        realm_addr = await realm.address()

    address = realm_addr.address
    is_nethernet = realm_addr.network_protocol and "NETHERNET" in realm_addr.network_protocol.upper()
    is_jsonrpc = is_nethernet and "JSONRPC" in realm_addr.network_protocol.upper()

    key = ec.generate_private_key(ec.SECP384R1())
    network = None
    multiplayer_token = ""

    if is_nethernet:
        from mcbe.auth.service import discover, request_service_token, request_multiplayer_token
        from mcbe.auth.playfab import login_with_xbox as playfab_login
        from mcbe.nethernet import create_network

        xbl_pf = await request_xbl_token(live_token, "http://playfab.xboxlive.com/")
        discovery = await discover()
        playfab_ticket = await playfab_login(xbl_pf, title_id=discovery.playfab_title_id)
        service_token = await request_service_token(
            discovery.auth_uri, xbl_pf.auth_header_value(),
            playfab_title_id=discovery.playfab_title_id,
            playfab_session_ticket=playfab_ticket,
        )
        multiplayer_token = await request_multiplayer_token(
            discovery.auth_uri, service_token, key.public_key(),
        )
        network = create_network(
            mc_token=service_token.authorization_header,
            signaling_url=discovery.signaling_info.service_uri,
            use_jsonrpc=is_jsonrpc,
            backend=backend,
        )
        backend_name = "libdatachannel" if "Ldc" in type(network).__name__ else "aiortc"
        logger.info("WebRTC バックエンド: %s", backend_name)

    xbl_mp = await request_xbl_token(live_token, "https://multiplayer.minecraft.net/")
    login_chain = await request_minecraft_chain(xbl_mp, key)

    logger.info("Realm アドレス: %s (プロトコル: %s)", address, realm_addr.network_protocol)
    return address, login_chain, key, multiplayer_token, network


# ── main ─────────────────────────────────────────────────────────


async def main(args: argparse.Namespace) -> None:
    _setup_logging(getattr(logging, args.log_level))

    state = MapState()
    block_colors = load_block_colors(getattr(args, "resource_pack", None), state=state)

    if args.proxy:
        await run_proxy(args.listen, args.remote, state, block_colors, args.web_port)
    else:
        await run_standalone(
            args.bds_address, state, block_colors, args.web_port,
            realms=args.realms, invite_code=args.invite_code,
            backend=args.backend,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="リアルタイム地図ビューア")
    parser.add_argument("--bds-address", default="127.0.0.1:19132")
    parser.add_argument("--realms", action="store_true")
    parser.add_argument("--invite-code", default=None)
    parser.add_argument("--backend", choices=["aiortc", "libdatachannel"], default=None)
    parser.add_argument("--proxy", action="store_true", help="proxy モード")
    parser.add_argument("--listen", default="0.0.0.0:19133", help="proxy: listen address")
    parser.add_argument("--remote", default="127.0.0.1:19132", help="proxy: remote address")
    parser.add_argument("--web-port", type=int, default=8080)
    parser.add_argument("--resource-pack", default=None, help="リソースパックパス")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING"], default="INFO")
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.info("停止")
