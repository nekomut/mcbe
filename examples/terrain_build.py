"""DEM地形配置ボット（並列対応）.

BDS に直接接続し、基盤地図情報 DEM5A から生成した地形を配置する。
複数ボットで並列配置し、途中終了しても次回レジュームできる。

初回のみ BDS コンソールで各ボットに /op を実行すること。
  例: ボット2体なら /op a と /op b

地形データ:
  - 原点: (36.104665°N, 140.087099°E) → MC座標 (0, 0, 0)
  - 解像度: 0.75m/ブロック (5m DEM を cubic spline で補間)
  - 基準標高: 16m (= Y=0)
  - MC座標: X+=東, Z+=南, Y+=上

Usage:
    python examples/terrain_build.py --address 127.0.0.1:19132 --bots 4
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from pymc.dial import Dialer
from pymc.raknet import RakNetNetwork
from pymc.proto.login.data import IdentityData
from pymc.proto.packet.command_request import CommandOrigin, CommandRequest, ORIGIN_PLAYER
from pymc.proto.packet.network_stack_latency import NetworkStackLatency

logger = logging.getLogger(__name__)

LOCAL_CONFIG = os.path.join(os.path.dirname(__file__), "local.json")
TERRAIN_JSON = os.path.join(os.path.dirname(__file__), "terrain.json")
HEIGHTMAP_CSV = os.path.join(os.path.dirname(__file__), "heightmap.csv")
BUILDINGMAP_CSV = os.path.join(os.path.dirname(__file__), "buildingmap.csv")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "heightmap.progress")
BUILDING_PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "building.progress")
BUILDING_BLOCK_TYPE = "quartz_block"
SCALE = 0.75  # メートル/ブロック — plot_dem3d.py と一致させること
BUILDING_HEIGHT = int(round(5.0 / SCALE))   # 物理5m → 7ブロック
BRIDGE_THICKNESS = 2                        # 橋の厚み（ブロック数）
CLEAR_HEIGHT = int(round(150.0 / SCALE))    # 物理150m → 200ブロック

# サーフェスタイプ → ブロック種別
SURFACE_BLOCKS = {
    0: "grass_block",  # 草地（デフォルト）
    1: "stone",        # 道路
    2: "water",        # 水域
}

# ボット名: a~z
BOT_NAMES = [chr(ord("a") + i) for i in range(26)]
# 各ボットに固定 UUID を割り当て
BOT_UUIDS = [f"b1e3a2f4-5c6d-7e8f-9a0b-1c2d3e4f5{i:03x}" for i in range(26)]
BOT_XUIDS = [f"{1000000000000000 + i}" for i in range(26)]


def extract_gamertag(login_chain: str) -> str:
    """login_chain JWT からゲーマータグ (displayName) を取得する."""
    import json as _json
    chain_data = _json.loads(login_chain)
    for token in chain_data.get("chain", []):
        claims = jwt.decode(token, options={"verify_signature": False})
        extra = claims.get("extraData", {})
        name = extra.get("displayName", "")
        if name:
            return name
    return ""


def load_terrain(json_path: str, csv_path: str) -> tuple[list[list[int]], list[list[int]] | None, list[list[int]] | None, list[list[int]] | None, list[list[int]] | None, list[list[int]] | None, int, int]:
    """地形データを読み込む. JSON があれば優先、なければ CSV にフォールバック.

    Returns: (heightmap, buildingmap, surfacemap, bridgemap, centerlinemap, roadcatmap, x_offset, z_offset)
    x_offset/z_offset は heightmap[0][0] の MC 座標。
    surfacemap: 0=草地, 1=道路, 2=水域 (None なら全て stone)。
    bridgemap: 橋がある座標 = 1 (None なら橋なし)。
    centerlinemap: 道路中心線 = 1 (None なら中心線なし)。
    roadcatmap: 主要道路(rdCtg 0-3) = 1 (None なら情報なし)。
    """
    if os.path.exists(json_path):
        with open(json_path) as f:
            data = json.load(f)
        heightmap = data["heightmap"]
        buildingmap = data.get("buildingmap")
        surfacemap = data.get("surfacemap")
        bridgemap = data.get("bridgemap")
        centerlinemap = data.get("centerlinemap")
        roadcatmap = data.get("roadcatmap")
        mc_start = data.get("mc_start", {})
        x_off = mc_start.get("x", 0)
        z_off = mc_start.get("z", 0)
        return heightmap, buildingmap, surfacemap, bridgemap, centerlinemap, roadcatmap, x_off, z_off

    # CSV フォールバック
    heightmap = []
    with open(csv_path) as f:
        for row in csv.reader(f):
            heightmap.append([int(v) for v in row])
    buildingmap = None
    if os.path.exists(BUILDINGMAP_CSV):
        buildingmap = []
        with open(BUILDINGMAP_CSV) as f:
            for row in csv.reader(f):
                buildingmap.append([int(v) for v in row])
    return heightmap, buildingmap, None, None, None, None, 0, 0


def load_progress(path: str) -> set[int]:
    """完了済み行番号を読み込む."""
    if not os.path.exists(path):
        return set()
    done = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                done.add(int(line))
    return done


def save_progress_line(path: str, z: int) -> None:
    """完了した行番号を追記する."""
    with open(path, "a") as f:
        f.write(f"{z}\n")


async def connect_bot(bot_id: int, address: str, *, login_chain: str | None = None, auth_key=None, multiplayer_token: str = "", network=None, gamertag: str = "") -> tuple:
    """1体のボットを接続してコネクションを返す."""
    name = gamertag or BOT_NAMES[bot_id]
    log = logging.getLogger(f"bot.{name}")

    if network is None:
        network = RakNetNetwork()
    dialer = Dialer(
        identity_data=IdentityData(
            display_name=name,
            identity=BOT_UUIDS[bot_id],
            xuid=BOT_XUIDS[bot_id],
        ),
        network=network,
        login_chain=login_chain,
        auth_key=auth_key,
        multiplayer_token=multiplayer_token,
    )

    conn = await dialer.dial(address)
    log.info("スポーン完了")
    return conn


def start_read_task(conn) -> asyncio.Task:
    """パケット読み取りタスクを開始する."""
    async def read_packets() -> None:
        try:
            while True:
                pk = await conn.read_packet()
                if isinstance(pk, NetworkStackLatency) and pk.needs_response:
                    await conn.write_packet(
                        NetworkStackLatency(timestamp=pk.timestamp, needs_response=False)
                    )
                    await conn.flush()
        except Exception:
            pass

    return asyncio.create_task(read_packets())


async def bot_worker(
    bot_id: int,
    conn,
    read_task: asyncio.Task,
    heightmap: list[list[int]],
    buildingmap: list[list[int]] | None,
    surfacemap: list[list[int]] | None,
    bridgemap: list[list[int]] | None,
    centerlinemap: list[list[int]] | None,
    roadcatmap: list[list[int]] | None,
    rows: list[int],
    phase: str,
    progress_file: str,
    stats: dict,
    x_offset: int = 0,
    z_offset: int = 0,
    *,
    bot_name: str | None = None,
) -> None:
    """1体のボットが担当行のブロックを配置する."""
    name = bot_name or BOT_NAMES[bot_id]
    log = logging.getLogger(f"bot.{name}")

    cmd_count = 0
    size_x = len(heightmap[0])

    def block_at(z: int, x: int) -> str:
        """surfacemap に基づいてブロック種別を返す."""
        if surfacemap is not None:
            return SURFACE_BLOCKS.get(surfacemap[z][x], "grass")
        return "stone"

    async def run_cmd(cmd: str) -> None:
        nonlocal cmd_count
        cmd_count += 1
        await conn.write_packet(
            CommandRequest(
                command_line=cmd,
                command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
                internal=False,
                version="latest",
            )
        )
        await conn.flush()
        await asyncio.sleep(0.01)

    try:
        for i, z in enumerate(rows):
            mc_z = z + z_offset
            if phase == "terrain":
                # 草地・水域フェーズ: 全セルを草地または水域として配置
                await run_cmd(f"/tp {name} {x_offset} {CLEAR_HEIGHT} {mc_z} -90 0")
                for x in range(size_x):
                    h_half = heightmap[z][x]
                    mc_x = x + x_offset
                    if h_half >= 0:
                        h = h_half // 2       # フルブロック高
                        slab = h_half % 2     # 1ならスラブあり
                        block = block_at(z, x)
                        # 草地・水域フェーズでは道路も草地として配置
                        if block == "stone":
                            block = "grass_block"
                        # 水域はスラブ不要
                        if block == "water":
                            slab = 0
                        top = h + slab
                        await run_cmd(f"/tp {name} {mc_x} {top + 5} {mc_z} -90 0")
                        # 標高±3ブロックを air に置換
                        air_bottom = max(0, h - 3)
                        air_top = h + 3
                        await run_cmd(f"/fill {mc_x} {air_bottom} {mc_z} {mc_x} {air_top} {mc_z} air")
                        if block == "water" and h >= 9:
                            # 水域: 上4=air, 5~7=water, 8~9=grass_block, 10以下=stone
                            await run_cmd(f"/fill {mc_x} 0 {mc_z} {mc_x} {h - 9} {mc_z} stone")
                            await run_cmd(f"/fill {mc_x} {h - 8} {mc_z} {mc_x} {h - 7} {mc_z} grass_block")
                            await run_cmd(f"/fill {mc_x} {h - 6} {mc_z} {mc_x} {h - 4} {mc_z} water")
                            await run_cmd(f"/fill {mc_x} {h - 3} {mc_z} {mc_x} {h} {mc_z} air")
                        elif block == "grass_block" and h >= 4:
                            # 草地: 上4=grass_block, 5以下=stone
                            await run_cmd(f"/fill {mc_x} 0 {mc_z} {mc_x} {h - 4} {mc_z} stone")
                            await run_cmd(f"/fill {mc_x} {h - 3} {mc_z} {mc_x} {h} {mc_z} grass_block")
                        else:
                            await run_cmd(f"/fill {mc_x} 0 {mc_z} {mc_x} {h} {mc_z} {block}")
                        # ハーフブロック配置（草地のみ）
                        if slab and block == "grass_block":
                            await run_cmd(
                                f"/setblock {mc_x} {h + 1} {mc_z} mossy_cobblestone_slab"
                            )
                        # 上空クリア
                        clear_from = top + 1
                        if clear_from <= CLEAR_HEIGHT:
                            await run_cmd(f"/fill {mc_x} {clear_from} {mc_z} {mc_x} {CLEAR_HEIGHT} {mc_z} air")
            elif phase == "road":
                # 道路・橋フェーズ: 道路セルを stone で上書き、橋セルも配置
                h0 = (heightmap[z][0] // 2) + (heightmap[z][0] % 2)
                await run_cmd(f"/tp {name} {x_offset} {h0 + 10} {mc_z} -90 0")
                for x in range(size_x):
                    mc_x = x + x_offset
                    is_bridge = bridgemap is not None and bridgemap[z][x] > 0
                    is_road = block_at(z, x) == "stone"
                    if not (is_bridge or is_road):
                        continue
                    if is_bridge:
                        h_half = bridgemap[z][x]
                    else:
                        h_half = heightmap[z][x]
                        if h_half < 0:
                            continue
                    h = h_half // 2
                    slab = h_half % 2
                    top = h + slab
                    await run_cmd(f"/tp {name} {mc_x} {top + 5} {mc_z} -90 0")
                    # 標高±3ブロックを air に置換
                    air_bottom = max(0, h - 3)
                    air_top = h + 3
                    await run_cmd(f"/fill {mc_x} {air_bottom} {mc_z} {mc_x} {air_top} {mc_z} air")
                    is_main = roadcatmap is not None and roadcatmap[z][x] == 1
                    top_block = "gray_concrete_powder" if is_main else "stone"
                    if is_bridge:
                        # 橋: 上2ブロック (最上面=top_block, その下=stone)
                        if h >= 1:
                            await run_cmd(f"/setblock {mc_x} {h - 1} {mc_z} stone")
                            await run_cmd(f"/setblock {mc_x} {h} {mc_z} {top_block}")
                        else:
                            await run_cmd(f"/setblock {mc_x} 0 {mc_z} {top_block}")
                    else:
                        # 道路: 最上面=top_block, その下=stone, 3~4=dirt, 5以下=stone
                        if h >= 5:
                            await run_cmd(f"/fill {mc_x} {h - 3} {mc_z} {mc_x} {h - 2} {mc_z} dirt")
                            await run_cmd(f"/fill {mc_x} {h - 1} {mc_z} {mc_x} {h - 1} {mc_z} stone")
                            await run_cmd(f"/setblock {mc_x} {h} {mc_z} {top_block}")
                        else:
                            if h >= 1:
                                await run_cmd(f"/fill {mc_x} 0 {mc_z} {mc_x} {h - 1} {mc_z} stone")
                            await run_cmd(f"/setblock {mc_x} {h} {mc_z} {top_block}")
                    # ハーフブロック配置
                    if slab:
                        slab_block = "cobbled_deepslate_slab" if is_main else "normal_stone_slab"
                        await run_cmd(f"/setblock {mc_x} {h + 1} {mc_z} {slab_block}")
            elif phase == "building" and buildingmap is not None:
                # 建物配置（heightmap は半ブロック単位）
                h0 = (heightmap[z][0] // 2) + (heightmap[z][0] % 2)
                await run_cmd(f"/tp {name} {x_offset} {h0 + BUILDING_HEIGHT + 5} {mc_z} -90 0")
                for x in range(size_x):
                    if buildingmap[z][x] == 1:
                        h_half = heightmap[z][x]
                        mc_x = x + x_offset
                        if h_half >= 0:
                            h = (h_half // 2) + (h_half % 2)  # スラブ込みの最上位Y
                            y_bottom = h + 1
                            y_top = h + BUILDING_HEIGHT
                            await run_cmd(f"/tp {name} {mc_x} {y_top + 5} {mc_z} -90 0")
                            await run_cmd(f"/setblock {mc_x} {h} {mc_z} stone")
                            await run_cmd(
                                f"/fill {mc_x} {y_bottom} {mc_z} {mc_x} {y_top} {mc_z} {BUILDING_BLOCK_TYPE}"
                            )
            elif phase == "centerline" and centerlinemap is not None:
                # まず既存のレッドストーンを stone に置換、その後新しいレッドストーンを配置
                h0 = (heightmap[z][0] // 2) + (heightmap[z][0] % 2)
                await run_cmd(f"/tp {name} {x_offset} {h0 + 5} {mc_z} -90 0")
                for x in range(size_x):
                    mc_x = x + x_offset
                    if bridgemap is not None and bridgemap[z][x] > 0:
                        bh = bridgemap[z][x]
                        top = (bh // 2) + (bh % 2)
                    else:
                        h_half = heightmap[z][x]
                        if h_half < 0:
                            continue
                        h = h_half // 2
                        slab = h_half % 2
                        top = h + slab
                    for db in ("redstone_block", "glowstone", "redstone_lamp",
                              "pearlescent_froglight", "verdant_froglight",
                              "ochre_froglight", "lit_pumpkin", "sea_lantern"):
                        await run_cmd(
                            f"/execute positioned {mc_x} {top} {mc_z} "
                            f"run fill {mc_x} {top} {mc_z} {mc_x} {top} {mc_z} stone replace {db}")
                # レッドストーン / グロウストーン配置
                for x in range(size_x):
                    cv = centerlinemap[z][x]
                    if cv == 0:
                        continue
                    mc_x = x + x_offset
                    if bridgemap is not None and bridgemap[z][x] > 0:
                        bh = bridgemap[z][x]
                        top = (bh // 2) + (bh % 2)
                    else:
                        h_half = heightmap[z][x]
                        if h_half < 0:
                            continue
                        h = h_half // 2
                        slab = h_half % 2
                        top = h + slab
                    block = {1: "redstone_block", 2: "glowstone", 3: "redstone_lamp",
                             4: "pearlescent_froglight", 5: "verdant_froglight",
                             6: "ochre_froglight", 7: "lit_pumpkin",  # 222x
                             8: "sea_lantern"}.get(cv, "redstone_block")
                    await run_cmd(f"/tp {name} {mc_x} {top + 5} {mc_z} -90 0")
                    await run_cmd(f"/setblock {mc_x} {top} {mc_z} {block}")
                    await run_cmd(f"/fill {mc_x} {top + 1} {mc_z} {mc_x} {top + 5} {mc_z} air")
            save_progress_line(progress_file, z)
            stats["done_rows"] += 1
            log.info("  [%s] 行完了: z=%d (mc: x=%d~%d, z=%d) (%d/%d) %d cmd",
                     phase, z, x_offset, x_offset + size_x - 1, mc_z, i + 1, len(rows), cmd_count)

        stats["cmd_total"] += cmd_count
        log.info("[%s] 担当完了! %d 行, %d コマンド", phase, len(rows), cmd_count)
    finally:
        read_task.cancel()
        try:
            await read_task
        except asyncio.CancelledError:
            pass
        await conn.close()


async def resolve_realms(invite_code: str | None = None) -> tuple[str, str, object, object | None]:
    """Realms に認証して接続先アドレス、login_chain、auth_key、Network を返す.

    Returns:
        (address, login_chain, auth_key, multiplayer_token, network)
    """
    from pymc.auth.live import get_live_token
    from pymc.auth.xbox import request_xbl_token
    from pymc.auth.minecraft import request_minecraft_chain
    from pymc.realms import RealmsClient

    live_token = await get_live_token()

    # Realms API 用トークン
    xbl_realms = await request_xbl_token(
        live_token, "https://pocket.realms.minecraft.net/",
    )

    # Realm アドレス取得
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

    network = None
    multiplayer_token = ""
    is_nethernet = realm_addr.network_protocol and "NETHERNET" in realm_addr.network_protocol.upper()
    is_jsonrpc = is_nethernet and "JSONRPC" in realm_addr.network_protocol.upper()

    # 認証キー生成（login chain と multiplayer token で共有）
    key = ec.generate_private_key(ec.SECP384R1())

    if is_nethernet:
        logger.info("NetherNet プロトコル検出: MCToken を取得中...")
        from pymc.auth.service import discover, request_service_token, request_multiplayer_token
        from pymc.nethernet.ldc_network import LdcNetherNetNetwork

        # PlayFab 認証: XBL → PlayFab SessionTicket → MCToken
        from pymc.auth.playfab import login_with_xbox as playfab_login

        xbl_pf = await request_xbl_token(live_token, "http://playfab.xboxlive.com/")

        # Discovery (環境自動解決)
        discovery = await discover()

        # PlayFab SessionTicket 取得
        playfab_ticket = await playfab_login(
            xbl_pf, title_id=discovery.playfab_title_id,
        )
        logger.info("PlayFab SessionTicket 取得完了")

        # MCToken (PlayFab tokenType で取得)
        service_token = await request_service_token(
            discovery.auth_uri,
            xbl_pf.auth_header_value(),
            playfab_title_id=discovery.playfab_title_id,
            playfab_session_ticket=playfab_ticket,
        )
        signaling_info = discovery.signaling_info
        logger.info("MCToken 取得完了")
        logger.info("シグナリング: %s", signaling_info.service_uri)

        # Multiplayer token (OIDC JWT) — Login パケットの Token フィールドに必要
        multiplayer_token = await request_multiplayer_token(
            discovery.auth_uri,
            service_token,
            key.public_key(),
        )
        logger.info("Multiplayer token 取得完了")

        # NetherNet ネットワーク (libdatachannel ネイティブ実装)
        network = LdcNetherNetNetwork(
            mc_token=service_token.authorization_header,
            signaling_url=signaling_info.service_uri,
            use_jsonrpc=is_jsonrpc,
        )

    # Minecraft 認証用トークン（login chain 取得）
    xbl_mp = await request_xbl_token(
        live_token, "https://multiplayer.minecraft.net/",
    )
    login_chain = await request_minecraft_chain(xbl_mp, key)

    logger.info("Realm アドレス: %s (プロトコル: %s)", address, realm_addr.network_protocol)
    return address, login_chain, key, multiplayer_token, network


async def main(address: str, num_bots: int, *, reset: bool = False, no_road: bool = False, no_building: bool = False, only_road: bool = False, only_building: bool = False, only_centerline: bool = False, realms: bool = False, invite_code: str | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if num_bots < 1 or num_bots > 26:
        logger.error("ボット数は 1~26 で指定してください")
        return

    login_chain = None
    auth_key = None
    multiplayer_token = ""
    realms_network = None
    realms_gamertag = None
    if realms:
        num_bots = 1
        logger.info("Realms モード: 認証中...")
        address, login_chain, auth_key, multiplayer_token, realms_network = await resolve_realms(invite_code)
        realms_gamertag = extract_gamertag(login_chain)
        if realms_gamertag:
            logger.info("ゲーマータグ: %s", realms_gamertag)

    if realms_network is None:
        # RakNet: ping で接続確認
        ping_network = RakNetNetwork()
        try:
            pong = await ping_network.ping(address)
            logger.info("サーバー発見: %s", pong.decode()[:80])
        except Exception as e:
            logger.error("サーバー応答なし: %s", e)
            return
    else:
        logger.info("NetherNet 接続: ping スキップ")

    heightmap, buildingmap, surfacemap, bridgemap, centerlinemap, roadcatmap, x_offset, z_offset = load_terrain(TERRAIN_JSON, HEIGHTMAP_CSV)
    size_z = len(heightmap)
    size_x = len(heightmap[0])
    source = "JSON" if os.path.exists(TERRAIN_JSON) else "CSV"
    logger.info("高さマップ: %dx%d (%s)", size_x, size_z, source)
    if x_offset or z_offset:
        logger.info("オフセット: X=%d, Z=%d", x_offset, z_offset)

    if surfacemap:
        logger.info("サーフェスマップ: あり (草地/道路/水域)")
    else:
        logger.info("サーフェスマップ: なし (全て stone)")

    if buildingmap:
        logger.info("建物マップ: %dx%d", len(buildingmap[0]), len(buildingmap))

    if bridgemap:
        logger.info("橋マップ: %dx%d", len(bridgemap[0]), len(bridgemap))

    if centerlinemap:
        logger.info("中心線マップ: あり (レッドストーン配置)")

    ROAD_PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "road.progress")
    CENTERLINE_PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "centerline.progress")

    # フェーズ判定: 地形 → 道路・橋 → 建物 → 中心線 の順に実行
    if reset:
        for pf in [PROGRESS_FILE, ROAD_PROGRESS_FILE,
                    BUILDING_PROGRESS_FILE, CENTERLINE_PROGRESS_FILE]:
            if os.path.exists(pf):
                os.remove(pf)
        logger.info("進捗リセット")

    phases = []

    has_only = only_road or only_building or only_centerline

    if not has_only:
        terrain_done = load_progress(PROGRESS_FILE) if not reset else set()
        terrain_remaining = [z for z in range(size_z) if z not in terrain_done]
        if terrain_remaining:
            phases.append(("terrain", terrain_remaining, PROGRESS_FILE))
        else:
            logger.info("地形: 全行配置済み")

    if (not has_only or only_road) and not no_road:
        if surfacemap or bridgemap:
            road_done = load_progress(ROAD_PROGRESS_FILE) if not reset else set()
            road_remaining = [z for z in range(size_z) if z not in road_done]
            if road_remaining:
                phases.append(("road", road_remaining, ROAD_PROGRESS_FILE))
            else:
                logger.info("道路・橋: 全行配置済み")

    if (not has_only or only_building) and not no_building:
        if buildingmap:
            building_done = load_progress(BUILDING_PROGRESS_FILE) if not reset else set()
            building_remaining = [z for z in range(size_z) if z not in building_done]
            if building_remaining:
                phases.append(("building", building_remaining, BUILDING_PROGRESS_FILE))
            else:
                logger.info("建物: 全行配置済み")

    if (not has_only or only_centerline) and centerlinemap:
        cl_done = load_progress(CENTERLINE_PROGRESS_FILE) if not reset else set()
        cl_remaining = [z for z in range(size_z) if z not in cl_done]
        if cl_remaining:
            phases.append(("centerline", cl_remaining, CENTERLINE_PROGRESS_FILE))
        else:
            logger.info("中心線: 全行配置済み")

    if not phases:
        logger.info("全フェーズ完了済みです。リセットするには .progress ファイルを削除してください。")
        return

    for phase_name, remaining, progress_file in phases:
        logger.info("=== %s フェーズ: 残り %d/%d 行 ===", phase_name, len(remaining), size_z)

        actual_bots = min(num_bots, len(remaining))
        chunks: list[list[int]] = [[] for _ in range(actual_bots)]
        for i, z in enumerate(remaining):
            chunks[i % actual_bots].append(z)

        if realms_gamertag:
            bot_names = [realms_gamertag]
        else:
            bot_names = [BOT_NAMES[i] for i in range(actual_bots)]
        logger.info("ボット %d 体: %s", actual_bots, ", ".join(bot_names))

        # ボットを1体ずつ順次接続
        connections = []
        read_tasks = []
        for i in range(actual_bots):
            logger.info("接続中: %s (%d/%d)...", bot_names[i], i + 1, actual_bots)
            conn = await connect_bot(i, address, login_chain=login_chain, auth_key=auth_key, multiplayer_token=multiplayer_token, network=realms_network, gamertag=realms_gamertag or "")
            read_task = start_read_task(conn)
            connections.append(conn)
            read_tasks.append(read_task)
            if i < actual_bots - 1:
                await asyncio.sleep(1)

        logger.info("全ボット接続完了!")
        if phase_name == phases[0][0]:  # 最初のフェーズのみ op を待つ
            logger.info("BDS コンソールで以下を実行してから Enter を押してください:")
            for n in bot_names:
                logger.info("  /op %s", n)
            # await asyncio.to_thread(input, "")
            await asyncio.sleep(1)

        stats = {"done_rows": 0, "cmd_total": 0}
        t_start = time.monotonic()

        async def progress_monitor(total: int) -> None:
            while stats["done_rows"] < total:
                await asyncio.sleep(2)
                elapsed = time.monotonic() - t_start
                done = stats["done_rows"]
                if done > 0:
                    eta = elapsed / done * (total - done)
                    logger.info("=== [%s] 全体進捗: %d/%d 行 (%.1f%%) 残り %d秒 ===",
                                phase_name, done, total, done / total * 100, int(eta))

        monitor = asyncio.create_task(progress_monitor(len(remaining)))

        await asyncio.gather(
            *(bot_worker(i, connections[i], read_tasks[i], heightmap, buildingmap,
                         surfacemap, bridgemap, centerlinemap, roadcatmap,
                         chunks[i], phase_name, progress_file,
                         stats, x_offset, z_offset,
                         bot_name=bot_names[i] if i < len(bot_names) else None)
              for i in range(actual_bots))
        )

        monitor.cancel()
        try:
            await monitor
        except asyncio.CancelledError:
            pass

        elapsed_total = time.monotonic() - t_start
        logger.info("=== [%s] 完了! %d 行, %.1f秒 ===", phase_name, len(remaining), elapsed_total)


if __name__ == "__main__":
    cfg = {}
    if os.path.exists(LOCAL_CONFIG):
        with open(LOCAL_CONFIG) as f:
            cfg = json.load(f)
    parser = argparse.ArgumentParser(description="DEM地形をMinecraftに配置する")
    parser.add_argument("--address", default=cfg.get("address", "127.0.0.1:19132"))
    parser.add_argument("--bots", type=int, default=4, help="並列ボット数 (default: 4, max: 26)")
    parser.add_argument("--reset", action="store_true", help="進捗をリセットして最初からやり直す")
    parser.add_argument("--no-road", action="store_true", help="道路・橋配置をスキップする")
    parser.add_argument("--no-building", action="store_true", help="建物配置をスキップする")
    parser.add_argument("--only-road", action="store_true", help="道路・橋配置のみ実行する")
    parser.add_argument("--only-building", action="store_true", help="建物配置のみ実行する")
    parser.add_argument("--only-centerline", action="store_true", help="レッドストーン配置のみ実行する")
    parser.add_argument("--realms", action="store_true", help="Realms に接続する（1ボット、Xbox Live 認証）")
    parser.add_argument("--invite-code", default=None, help="Realm の招待コード（省略時は最初の Realm）")
    args = parser.parse_args()
    asyncio.run(main(args.address, args.bots, reset=args.reset, no_road=args.no_road, no_building=args.no_building, only_road=args.only_road, only_building=args.only_building, only_centerline=args.only_centerline, realms=args.realms, invite_code=args.invite_code))
