"""地理院タイルから Minecraft 地形データを生成する.

DEM5A 標高タイル（txt）+ ベクトルタイル（pbf）から terrain.json を出力。
GML ファイル不要。緯度経度を指定するだけで任意の場所の地形を生成できる。
出力は terrain_build.py と互換。

Usage:
    python examples/terrain_gen.py --lat 36.104665 --lon 140.087099
    python examples/terrain_gen.py --lat 35.6895 --lon 139.6917 --width 500 --height 500
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.request

import numpy as np
from matplotlib.path import Path

LOCAL_CONFIG = os.path.join(os.path.dirname(__file__), "local.json")


def load_local_config() -> dict:
    """ローカル設定ファイルを読み込む（なければ空辞書）."""
    if os.path.exists(LOCAL_CONFIG):
        with open(LOCAL_CONFIG) as f:
            return json.load(f)
    return {}
from scipy.interpolate import RectBivariateSpline
from scipy.ndimage import distance_transform_edt, label as ndimage_label

try:
    import mapbox_vector_tile
except ImportError:
    print("mapbox-vector-tile が必要です: pip install mapbox-vector-tile")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
NODATA = -9999.0
SURFACE_GRASS = 0
SURFACE_ROAD = 1
SURFACE_WATER = 2

DEM_ZOOM = 15
DEM_TILE_SIZE = 256
VECTOR_ZOOM_EDGE = 15   # 道路縁線 (z=15)
VECTOR_ZOOM_EXTRA = 16   # 追加道路縁線 (z=16, ftCode 22xx も縁線扱い)

DEM_URL = "https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt"
VECTOR_URL = "https://cyberjapandata.gsi.go.jp/xyz/experimental_bvmap/{z}/{x}/{y}.pbf"

# 道路縁の ftCode（Voronoi 法で面を復元）
# 2701=真幅道路, 2703/2704=亜種, 2711=軽車道, 2721=徒歩道, 2723=亜種, 2731=庭園路等
ROAD_EDGE_CODES = {2701, 2703, 2704, 2711, 2713, 2721, 2723, 2731, 2733}
# z=16 の ftCode 22xx は名目上「中心線」だが実際は縁線の近くを走る → 追加縁線として扱う
ROAD_EXTRA_EDGE_CODES = {2201, 2203, 2221}

# ---------------------------------------------------------------------------
# タイル座標ヘルパー
# ---------------------------------------------------------------------------

def latlon_to_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    tx = int((lon + 180) / 360 * n)
    lat_rad = math.radians(lat)
    ty = int((1 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad))
              / math.pi) / 2 * n)
    return tx, ty


def tile_to_latlon(tx: int, ty: int, z: int) -> tuple[float, float]:
    n = 2 ** z
    lon = tx / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * ty / n))))
    return lat, lon


CACHE_DIR = os.path.join(os.path.dirname(__file__), ".tile_cache")


def fetch_url(url: str) -> bytes | None:
    # ファイルキャッシュ
    cache_key = url.replace("https://", "").replace("http://", "").replace("/", "_")
    cache_path = os.path.join(CACHE_DIR, cache_key)
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            data = f.read()
        return data if data else None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 404 もキャッシュ（空ファイル）
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_path, "wb") as f:
                pass
            return None
        raise
    except Exception:
        return None
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "wb") as f:
        f.write(data)
    return data

# ---------------------------------------------------------------------------
# DEM タイル
# ---------------------------------------------------------------------------

def parse_dem_txt(txt: str) -> np.ndarray:
    """DEM5A txt (256×256 CSV) → elevation 配列."""
    rows = []
    for line in txt.strip().split("\n"):
        vals = []
        for v in line.split(","):
            v = v.strip()
            if v == "e" or v == "":
                vals.append(NODATA)
            else:
                vals.append(float(v))
        rows.append(vals)
    return np.array(rows)


def fetch_dem(origin_lat: float, origin_lon: float,
              mc_x_start: int, mc_z_start: int,
              nx: int, nz: int, scale: float,
              blocks_per_deg_lat: float, blocks_per_deg_lon: float,
              ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """DEM タイルを取得・結合して cubic spline 補間.

    Returns: (interp, dem_x, dem_z)
        interp: (nz, nx) 標高配列 [m]
        dem_x, dem_z: DEM グリッドの MC ブロック座標 (flatten_roads 用)
    """
    # MC 範囲 → 緯度経度範囲
    lon_min = origin_lon + mc_x_start / blocks_per_deg_lon
    lon_max = origin_lon + (mc_x_start + nx) / blocks_per_deg_lon
    lat_max = origin_lat - mc_z_start / blocks_per_deg_lat   # 北
    lat_min = origin_lat - (mc_z_start + nz) / blocks_per_deg_lat  # 南

    margin = 0.005
    z = DEM_ZOOM
    tx_min, _ = latlon_to_tile(lat_max + margin, lon_min - margin, z)
    tx_max, _ = latlon_to_tile(lat_min - margin, lon_max + margin, z)
    _, ty_min = latlon_to_tile(lat_max + margin, lon_min - margin, z)
    _, ty_max = latlon_to_tile(lat_min - margin, lon_max + margin, z)
    if tx_min > tx_max:
        tx_min, tx_max = tx_max, tx_min
    if ty_min > ty_max:
        ty_min, ty_max = ty_max, ty_min

    n_tx = tx_max - tx_min + 1
    n_ty = ty_max - ty_min + 1
    print(f"DEM タイル: z={z}, {n_tx}×{n_ty} ({n_tx * n_ty} 枚)")

    merged = np.full((n_ty * DEM_TILE_SIZE, n_tx * DEM_TILE_SIZE), NODATA)
    for ty in range(ty_min, ty_max + 1):
        for tx in range(tx_min, tx_max + 1):
            url = DEM_URL.format(z=z, x=tx, y=ty)
            data = fetch_url(url)
            if data is None:
                print(f"  DEM {z}/{tx}/{ty}: データなし")
                continue
            tile = parse_dem_txt(data.decode("utf-8"))
            iy = (ty - ty_min) * DEM_TILE_SIZE
            ix = (tx - tx_min) * DEM_TILE_SIZE
            h, w = tile.shape
            merged[iy:iy + h, ix:ix + w] = tile
            valid = tile[tile != NODATA]
            if valid.size > 0:
                print(f"  DEM {z}/{tx}/{ty}: {valid.min():.1f}–{valid.max():.1f} m")
            else:
                print(f"  DEM {z}/{tx}/{ty}: 全て nodata")

    # 各ピクセルの緯度経度 → MC ブロック座標
    lat_top, lon_left = tile_to_latlon(tx_min, ty_min, z)
    lat_bot, lon_right = tile_to_latlon(tx_max + 1, ty_max + 1, z)
    total_h, total_w = merged.shape
    lat_arr = np.linspace(lat_top, lat_bot, total_h)
    lon_arr = np.linspace(lon_left, lon_right, total_w)
    dem_x = (lon_arr - origin_lon) * blocks_per_deg_lon  # MC X 座標
    dem_z = (origin_lat - lat_arr) * blocks_per_deg_lat  # MC Z 座標

    # NODATA 埋め
    nodata_mask = merged == NODATA
    if nodata_mask.all():
        raise ValueError("DEM データが取得できませんでした")
    if nodata_mask.any():
        _, nearest_idx = distance_transform_edt(
            nodata_mask, return_distances=True, return_indices=True)
        merged[nodata_mask] = merged[tuple(nearest_idx[:, nodata_mask])]

    valid = merged[merged != NODATA]
    print(f"DEM 範囲: {valid.min():.1f}–{valid.max():.1f} m")

    # Cubic spline 補間
    spline = RectBivariateSpline(dem_z, dem_x, merged, kx=3, ky=3)
    block_x = np.arange(mc_x_start, mc_x_start + nx, 1.0)
    block_z = np.arange(mc_z_start, mc_z_start + nz, 1.0)
    # DEM 範囲にクランプ
    block_x = np.clip(block_x, dem_x.min(), dem_x.max())
    block_z = np.clip(block_z, dem_z.min(), dem_z.max())
    interp = spline(block_z, block_x)
    print(f"補間: {nx}×{nz} ブロック ({scale}m/block)")

    return interp, dem_x, dem_z, merged

# ---------------------------------------------------------------------------
# ベクトルタイル
# ---------------------------------------------------------------------------

def _fetch_vector_tiles(origin_lat: float, origin_lon: float,
                        mc_x_start: int, mc_z_start: int,
                        nx: int, nz: int,
                        blocks_per_deg_lat: float, blocks_per_deg_lon: float,
                        zoom: int, layers: set[str],
                        ) -> list[tuple[str, dict, dict]]:
    """指定ズームのベクトルタイルを取得し (layer_name, geom, props) のリストを返す."""
    lon_min = origin_lon + mc_x_start / blocks_per_deg_lon
    lon_max = origin_lon + (mc_x_start + nx) / blocks_per_deg_lon
    lat_max = origin_lat - mc_z_start / blocks_per_deg_lat
    lat_min = origin_lat - (mc_z_start + nz) / blocks_per_deg_lat

    margin = 0.005
    tx_min, _ = latlon_to_tile(lat_max + margin, lon_min - margin, zoom)
    tx_max, _ = latlon_to_tile(lat_min - margin, lon_max + margin, zoom)
    _, ty_min = latlon_to_tile(lat_max + margin, lon_min - margin, zoom)
    _, ty_max = latlon_to_tile(lat_min - margin, lon_max + margin, zoom)
    if tx_min > tx_max:
        tx_min, tx_max = tx_max, tx_min
    if ty_min > ty_max:
        ty_min, ty_max = ty_max, ty_min

    n_tx = tx_max - tx_min + 1
    n_ty = ty_max - ty_min + 1
    print(f"  z={zoom}: {n_tx}×{n_ty} ({n_tx * n_ty} 枚)")

    results = []
    n = 2 ** zoom
    for ty in range(ty_min, ty_max + 1):
        for tx in range(tx_min, tx_max + 1):
            url = VECTOR_URL.format(z=zoom, x=tx, y=ty)
            data = fetch_url(url)
            if data is None:
                continue
            decoded = mapbox_vector_tile.decode(
                data, default_options={"y_coord_down": True})

            for layer_name, layer in decoded.items():
                if layer_name not in layers:
                    continue
                extent = layer.get("extent", 4096)
                for feat in layer["features"]:
                    geom = feat["geometry"]
                    props = feat.get("properties", {})
                    gtype = geom["type"]
                    coords = geom["coordinates"]

                    def to_mc(x, y, _tx=tx, _ty=ty, _ext=extent, _n=n):
                        lo = (_tx + x / _ext) / _n * 360 - 180
                        la_rad = math.atan(math.sinh(
                            math.pi * (1 - 2 * (_ty + y / _ext) / _n)))
                        la = math.degrees(la_rad)
                        return ((lo - origin_lon) * blocks_per_deg_lon,
                                (origin_lat - la) * blocks_per_deg_lat)

                    def convert_ring(ring):
                        return [to_mc(p[0], p[1]) for p in ring]

                    # geometry 座標を MC 座標に変換
                    if gtype == "LineString":
                        mc_geom = {"type": gtype,
                                   "coordinates": convert_ring(coords)}
                    elif gtype == "MultiLineString":
                        mc_geom = {"type": gtype,
                                   "coordinates": [convert_ring(l) for l in coords]}
                    elif gtype == "Polygon":
                        mc_geom = {"type": gtype,
                                   "coordinates": [convert_ring(r) for r in coords]}
                    elif gtype == "MultiPolygon":
                        mc_geom = {"type": gtype,
                                   "coordinates": [[convert_ring(r) for r in p]
                                                    for p in coords]}
                    else:
                        continue
                    results.append((layer_name, mc_geom, props))
    return results


def fetch_vectors(origin_lat: float, origin_lon: float,
                  mc_x_start: int, mc_z_start: int,
                  nx: int, nz: int,
                  blocks_per_deg_lat: float, blocks_per_deg_lon: float,
                  ) -> tuple[list, list, list]:
    """ベクトルタイルからフィーチャーを取得し MC 座標に変換.

    z=15 から道路縁線・水域・建物を、z=16 から追加縁線を取得する。
    z=16 の ftCode 22xx は名目上「中心線」だが実際は縁線近傍を走るため
    追加の道路縁線として Voronoi に投入する。

    Returns: (road_lines, water_polys, building_polys)
        road_lines: [(mc_coords, ftCode), ...]
        water_polys, building_polys: [mc_coords, ...]
    """
    print("ベクトルタイル取得:")

    # z=15: 道路縁線 + 水域 + 建物
    feats_z15 = _fetch_vector_tiles(
        origin_lat, origin_lon, mc_x_start, mc_z_start, nx, nz,
        blocks_per_deg_lat, blocks_per_deg_lon,
        VECTOR_ZOOM_EDGE, {"road", "waterarea", "building"})

    # z=16: 追加道路縁線（22xx + 27xx）
    feats_z16 = _fetch_vector_tiles(
        origin_lat, origin_lon, mc_x_start, mc_z_start, nx, nz,
        blocks_per_deg_lat, blocks_per_deg_lon,
        VECTOR_ZOOM_EXTRA, {"road"})

    road_lines: list[tuple[list, int, int, int]] = []
    water_polys: list[list] = []
    building_polys: list[list] = []

    def extract_lines(geom):
        if geom["type"] == "LineString":
            return [geom["coordinates"]]
        elif geom["type"] == "MultiLineString":
            return geom["coordinates"]
        return []

    def extract_polys(geom):
        if geom["type"] == "Polygon":
            return [geom["coordinates"][0]]
        elif geom["type"] == "MultiPolygon":
            return [p[0] for p in geom["coordinates"]]
        return []

    # z=15: 道路線（27xx/22xx すべて取得）
    for layer_name, geom, props in feats_z15:
        if layer_name == "road":
            ft = props.get("ftCode", 0)
            if not (2200 <= ft < 2300 or 2400 <= ft < 2500 or 2700 <= ft < 2800):
                continue
            rdctg = props.get("rdCtg", -1)
            rnkw = props.get("rnkWidth", -1)
            for line in extract_lines(geom):
                road_lines.append((line, ft, rdctg, rnkw))
        elif layer_name == "waterarea":
            water_polys.extend(extract_polys(geom))
        elif layer_name == "building":
            building_polys.extend(extract_polys(geom))

    z15_count = len(road_lines)

    # z=16: 追加道路線（27xx/22xx すべて取得）
    for layer_name, geom, props in feats_z16:
        if layer_name == "road":
            ft = props.get("ftCode", 0)
            if not (2200 <= ft < 2300 or 2400 <= ft < 2500 or 2700 <= ft < 2800):
                continue
            rdctg = props.get("rdCtg", -1)
            rnkw = props.get("rnkWidth", -1)
            for line in extract_lines(geom):
                road_lines.append((line, ft, rdctg, rnkw))

    z16_count = len(road_lines) - z15_count
    print(f"  道路縁線 z={VECTOR_ZOOM_EDGE}: {z15_count} 本")
    print(f"  追加縁線 z={VECTOR_ZOOM_EXTRA}: {z16_count} 本")
    print(f"  水域: {len(water_polys)} 面")
    print(f"  建物: {len(building_polys)} 棟")
    return road_lines, water_polys, building_polys

# ---------------------------------------------------------------------------
# ラスタライズ
# ---------------------------------------------------------------------------

def rasterize_polygons(polys: list[list], shape: tuple[int, int],
                       mc_x_start: int, mc_z_start: int) -> np.ndarray:
    """ポリゴンリスト → boolean マスク (matplotlib Path)."""
    ny, nx = shape
    mask = np.zeros(shape, dtype=bool)
    for mc_coords in polys:
        # 配列インデックス座標に変換
        idx_coords = [(x - mc_x_start, z - mc_z_start) for x, z in mc_coords]
        xs = [c[0] for c in idx_coords]
        zs = [c[1] for c in idx_coords]
        if max(xs) < 0 or min(xs) >= nx or max(zs) < 0 or min(zs) >= ny:
            continue
        mpl_path = Path(idx_coords)
        x_min = max(0, int(min(xs)))
        x_max = min(nx - 1, int(max(xs)) + 1)
        z_min = max(0, int(min(zs)))
        z_max = min(ny - 1, int(max(zs)) + 1)
        if x_min > x_max or z_min > z_max:
            continue
        grid_x, grid_z = np.meshgrid(
            np.arange(x_min, x_max + 1), np.arange(z_min, z_max + 1))
        points = np.column_stack([grid_x.ravel(), grid_z.ravel()])
        hit = mpl_path.contains_points(points).reshape(grid_z.shape)
        mask[z_min:z_max + 1, x_min:x_max + 1] |= hit
    return mask

# ---------------------------------------------------------------------------
# サーフェスマップ生成
# ---------------------------------------------------------------------------

def gen_maps(road_lines: list, water_polys: list, building_polys: list,
             shape: tuple[int, int], mc_x_start: int, mc_z_start: int,
             scale: float, *, debug: bool = False, no_fill: bool = False, fill: bool = False,
             ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    """道路・水域・建物からサーフェスマップ・建物マップ・橋マップを生成.

    Returns: (surfacemap, buildingmap, bridgemap, centerlinemap, roadcatmap)
        centerlinemap: debug=True のとき、道路中心線の boolean マップ (int8)。
        roadcatmap: rdCtg 0-3 の道路セルを示すマップ (int8)。
    """
    ny, nx = shape
    surface = np.full(shape, SURFACE_GRASS, dtype=np.int8)

    # --- 水域 ---
    if water_polys:
        water_mask = rasterize_polygons(water_polys, shape, mc_x_start, mc_z_start)
        surface[water_mask] = SURFACE_WATER
        print(f"水域セル: {int(water_mask.sum())}/{ny * nx}")
    else:
        water_mask = np.zeros(shape, dtype=bool)
        print(f"水域セル: 0/{ny * nx}")

    # --- 建物 ---
    buildingmap = None
    if building_polys:
        buildingmap = rasterize_polygons(
            building_polys, shape, mc_x_start, mc_z_start).astype(np.int8)
        print(f"建物セル: {int(buildingmap.sum())}/{ny * nx}")
    else:
        print(f"建物セル: 0/{ny * nx}")

    # --- 道路 (領域ラベリング法) ---
    max_road_half_width = 6.6 / scale

    def rasterize_to_mask(mc_coords, arr, val=True):
        """線分を配列にラスタライズ."""
        for k in range(len(mc_coords) - 1):
            x0, z0 = mc_coords[k]
            x1, z1 = mc_coords[k + 1]
            ix0, iz0 = x0 - mc_x_start, z0 - mc_z_start
            ix1, iz1 = x1 - mc_x_start, z1 - mc_z_start
            seg_len = max(abs(ix1 - ix0), abs(iz1 - iz0))
            if seg_len < 0.5:
                continue
            steps = int(seg_len * 2) + 1
            for t in np.linspace(0, 1, steps):
                ix = int(round(ix0 + t * (ix1 - ix0)))
                iz = int(round(iz0 + t * (iz1 - iz0)))
                if 0 <= ix < nx and 0 <= iz < ny:
                    arr[iz, ix] = val

    # 22xx/24xx（道路中心線）と 270x（通常道路縁線）をラスタライズ
    edge_22xx = np.zeros(shape, dtype=bool)
    marker_270x = np.zeros(shape, dtype=bool)
    marker_main_road = np.zeros(shape, dtype=bool)  # rdCtg 0-3 の道路線
    all_road_lines = np.zeros(shape, dtype=bool)  # 全道路線（27xx 含む）
    for mc_coords, ft_code, rdctg, rnkw in road_lines:
        if 2200 <= ft_code < 2300 or 2400 <= ft_code < 2500:
            rasterize_to_mask(mc_coords, edge_22xx, val=True)
            rasterize_to_mask(mc_coords, all_road_lines, val=True)
        elif 2700 <= ft_code < 2710:
            if rnkw == 0 and not fill:
                # 細い道（rnkWidth=0）は領域充填せず線のみ
                rasterize_to_mask(mc_coords, all_road_lines, val=True)
            else:
                rasterize_to_mask(mc_coords, marker_270x, val=True)
                rasterize_to_mask(mc_coords, all_road_lines, val=True)
                if rdctg in (0, 1, 3):
                    rasterize_to_mask(mc_coords, marker_main_road, val=True)
        elif 2700 <= ft_code < 2800:
            rasterize_to_mask(mc_coords, all_road_lines, val=True)

    # 道路面の生成
    from scipy.ndimage import binary_dilation, convolve
    if no_fill:
        # 領域ラベリングをスキップ: ラスタライズした線のみ
        road_filled = edge_22xx | marker_270x | all_road_lines
        print(f"  道路縁線(線のみ): 22xx={int(edge_22xx.sum())}, 270x={int(marker_270x.sum())}")
    else:
        # 22xx で区切られた領域をラベリングし、270x を含む領域 = 道路面
        regions, n_regions = ndimage_label(~edge_22xx)
        road_region_ids = set(np.unique(regions[marker_270x]))
        road_region_ids.discard(0)
        road_side = np.isin(regions, list(road_region_ids)) if road_region_ids else np.zeros(shape, dtype=bool)
        # 22xx からの距離で制限
        dist_to_22 = distance_transform_edt(~edge_22xx)
        road_filled = road_side & (dist_to_22 <= max_road_half_width)
        road_filled |= edge_22xx & (dist_to_22 == 0)  # 22xx 自体も含める
        road_filled |= marker_270x  # 270x 自体も含める
        # 細い道（271x-273x）は線のみ道路扱い
        road_filled |= all_road_lines

        # 穴埋め（通常道路近傍のみ）
        dist_to_270 = distance_transform_edt(~marker_270x)
        normal_road_area = dist_to_270 <= max_road_half_width
        kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int8)
        edge_nbr = convolve(edge_22xx.astype(np.int8), kernel, mode='constant')
        one_block_gap = ~edge_22xx & (edge_nbr >= 2)
        road_filled |= one_block_gap & normal_road_area
        for _ in range(3):
            rs_nbr = convolve(road_filled.astype(np.int8), kernel, mode='constant')
            road_filled |= ~road_filled & (rs_nbr >= 3) & normal_road_area

        print(f"  道路縁線: 22xx={int(edge_22xx.sum())}, 270x={int(marker_270x.sum())}, "
              f"領域: {len(road_region_ids)}/{n_regions}")

    # rdCtg 0-3 の道路セルマスク（主要道路）
    if marker_main_road.any():
        dist_to_main = distance_transform_edt(~marker_main_road)
        main_road_mask = road_filled & (dist_to_main <= max_road_half_width)
    else:
        main_road_mask = np.zeros(shape, dtype=bool)
    roadcatmap = main_road_mask.astype(np.int8) if main_road_mask.any() else None

    # 橋 = 道路が水域を横断する箇所（road_filled と水域の重なり）
    bridge_mask = road_filled & water_mask
    if road_filled.any():
        surface[road_filled & ~water_mask] = SURFACE_ROAD

    road_count = int((surface == SURFACE_ROAD).sum())
    bridge_count = int(bridge_mask.sum())
    main_road_count = int(main_road_mask.sum())
    grass_count = int((surface == SURFACE_GRASS).sum())
    print(f"道路セル: {road_count}/{ny * nx} (主要道路: {main_road_count})")
    print(f"橋セル: {bridge_count}/{ny * nx}")
    print(f"草地セル: {grass_count}/{ny * nx}")

    bridgemap = bridge_mask.astype(np.int8) if bridge_count > 0 else None

    # 中心線マップ (debug 用) — 道路・橋ロジックとは独立した領域ラベリング
    centerlinemap = None
    if debug:
        # 22xx/24xx（道路縁線）
        dbg_edge_22xx = np.zeros(shape, dtype=bool)
        for mc_coords, ft_code, _, _ in road_lines:
            if 2200 <= ft_code < 2300 or 2400 <= ft_code < 2500:
                rasterize_to_mask(mc_coords, dbg_edge_22xx, val=True)

        # 270x のみ（通常道路）— 細い道 271x-273x と rdCtg=5/rnkWidth=0 は充填対象外
        dbg_marker_270x = np.zeros(shape, dtype=bool)
        for mc_coords, ft_code, rdctg, rnkw in road_lines:
            if 2700 <= ft_code < 2710 and (rnkw != 0 or fill):
                rasterize_to_mask(mc_coords, dbg_marker_270x, val=True)

        # 22xx で区切られた領域をラベリング
        dbg_regions, dbg_n_regions = ndimage_label(~dbg_edge_22xx)
        # 270x が含まれる領域 = 道路側
        road_region_ids = set(np.unique(dbg_regions[dbg_marker_270x]))
        road_region_ids.discard(0)
        dbg_road_side = np.isin(dbg_regions, list(road_region_ids)) if road_region_ids else np.zeros(shape, dtype=bool)
        # 22xx からの距離で制限
        dbg_dist_to_22 = distance_transform_edt(~dbg_edge_22xx)
        filled = dbg_road_side & (dbg_dist_to_22 <= max_road_half_width)
        filled |= dbg_edge_22xx & (dbg_dist_to_22 == 0)  # 22xx 自体も含める
        filled |= dbg_marker_270x  # 270x 自体も含める

        # 穴埋め（通常道路のみ、細い道 271x-273x は除外）
        dbg_kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int8)
        dbg_edge_nbr = convolve(dbg_edge_22xx.astype(np.int8), dbg_kernel, mode='constant')
        one_block_gap = ~dbg_edge_22xx & (dbg_edge_nbr >= 2)
        dbg_dist_to_270 = distance_transform_edt(~dbg_marker_270x)
        dbg_normal_area = dbg_dist_to_270 <= max_road_half_width
        filled |= one_block_gap & dbg_normal_area
        for _ in range(3):
            dbg_nbr = convolve(filled.astype(np.int8), dbg_kernel, mode='constant')
            filled |= ~filled & (dbg_nbr >= 3) & dbg_normal_area

        # 背景として redstone_lamp (値3) を設定
        # 0=なし, 1=redstone_block(22xx), 2=glowstone(270x),
        # 3=redstone_lamp(充填面), 4=pearlescent_froglight(271x),
        # 5=verdant_froglight(272x), 6=ochre_froglight(273x),
        # 7=lit_pumpkin(222x), 8=sea_lantern(24xx)
        center_val = np.zeros(shape, dtype=np.int8)
        center_val[filled] = 3

        # ftCode 別ライン描画（背景を上書き）
        ft_counts: dict[int, int] = {}
        for mc_coords, ft_code, _, _ in road_lines:
            if 2700 <= ft_code < 2710:
                v = 2
            elif 2710 <= ft_code < 2720:
                v = 4
            elif 2720 <= ft_code < 2730:
                v = 5
            elif 2730 <= ft_code < 2740:
                v = 6
            elif 2220 <= ft_code < 2230:
                v = 7
            elif 2400 <= ft_code < 2500:
                v = 8
            elif 2200 <= ft_code < 2300:
                v = 1
            else:
                continue
            before = int((center_val == v).sum())
            rasterize_to_mask(mc_coords, center_val, val=v)
            ft_counts[ft_code] = ft_counts.get(ft_code, 0) + int((center_val == v).sum()) - before
        centerlinemap = center_val
        fill_count = int(filled.sum())
        total = int((center_val > 0).sum())
        print(f"debug道路セル: {total}/{ny * nx} "
              f"(fill: {fill_count}, "
              f"redstone: {int((center_val == 1).sum())}, "
              f"glowstone: {int((center_val == 2).sum())}, "
              f"lamp: {int((center_val == 3).sum())})")
        for ft, cnt in sorted(ft_counts.items()):
            print(f"  ftCode {ft}: {cnt} セル")

    return surface, buildingmap, bridgemap, centerlinemap, roadcatmap

# ---------------------------------------------------------------------------
# 後処理
# ---------------------------------------------------------------------------

def flatten_roads(interp: np.ndarray, surfacemap: np.ndarray,
                  dem_data: np.ndarray, dem_x: np.ndarray, dem_z: np.ndarray,
                  mc_x_start: int, mc_z_start: int) -> None:
    """道路セルの高さを道路のみの線形補間に置換."""
    ny, nx = interp.shape
    dem_ny, dem_nx = dem_data.shape

    # DEM グリッド解像度で道路マスク作成
    dem_road = np.zeros(dem_data.shape, dtype=bool)
    for di in range(dem_ny):
        bi = int(round(dem_z[di])) - mc_z_start
        for dj in range(dem_nx):
            bj = int(round(dem_x[dj])) - mc_x_start
            if 0 <= bi < ny and 0 <= bj < nx:
                if surfacemap[bi, bj] == SURFACE_ROAD:
                    dem_road[di, dj] = True

    non_road = ~dem_road
    if non_road.all():
        print("道路平坦化: DEM上に道路点なし — スキップ")
        return

    data = dem_data.copy()
    if non_road.any():
        dist, nearest_idx = distance_transform_edt(
            non_road, return_distances=True, return_indices=True)
        max_replace_dist = 5
        close = non_road & (dist <= max_replace_dist)
        data[close] = data[nearest_idx[0][close], nearest_idx[1][close]]

    linear = RectBivariateSpline(dem_z, dem_x, data, kx=1, ky=1)
    new_x = np.arange(mc_x_start, mc_x_start + nx, 1.0)
    new_z = np.arange(mc_z_start, mc_z_start + ny, 1.0)
    new_x = np.clip(new_x, dem_x.min(), dem_x.max())
    new_z = np.clip(new_z, dem_z.min(), dem_z.max())
    linear_interp = linear(new_z, new_x)

    road_mask = surfacemap == SURFACE_ROAD
    interp[road_mask] = linear_interp[road_mask]
    print(f"道路平坦化: {int(road_mask.sum())} セル "
          f"(DEM道路点: {int(dem_road.sum())}/{dem_data.size})")


def adjust_bridge_heights(interp: np.ndarray, surfacemap: np.ndarray,
                          bridgemap: np.ndarray | None) -> None:
    """橋セルの高さを隣接道路セルの高さに合わせる."""
    if bridgemap is None:
        return
    bridge_mask = bridgemap.astype(bool)
    road_mask = surfacemap == SURFACE_ROAD
    if not bridge_mask.any() or not road_mask.any():
        return
    _, nearest_idx = distance_transform_edt(
        ~road_mask, return_distances=True, return_indices=True)
    road_height = interp[nearest_idx[0], nearest_idx[1]]
    interp[bridge_mask] = road_height[bridge_mask]
    print(f"橋高さ調整: {int(bridge_mask.sum())} セルを隣接道路の高さに設定")


def smooth_road_bridge(interp: np.ndarray, surfacemap: np.ndarray,
                       bridgemap: np.ndarray | None, scale: float) -> None:
    """道路・橋セルを拡散法で平滑化する."""
    ny, nx = interp.shape
    mask = surfacemap == SURFACE_ROAD
    if bridgemap is not None:
        mask = mask | bridgemap.astype(bool)
    if not mask.any():
        return

    alpha = 0.4
    max_step = scale / 4
    max_change = 0.0
    for iteration in range(500):
        neighbor_sum = np.zeros((ny, nx))
        neighbor_count = np.zeros((ny, nx))
        for dz, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nz_ = np.clip(np.arange(ny)[:, None] + dz, 0, ny - 1)
            nx_ = np.clip(np.arange(nx)[None, :] + dx, 0, nx - 1)
            both = mask & mask[nz_, nx_]
            neighbor_sum += interp[nz_, nx_] * both
            neighbor_count += both
        has_neighbor = neighbor_count > 0
        safe_count = np.where(has_neighbor, neighbor_count, 1)
        avg = np.where(has_neighbor, neighbor_sum / safe_count, interp)
        new_val = interp * (1 - alpha) + avg * alpha
        update = mask & has_neighbor
        max_change = np.max(np.abs(new_val[update] - interp[update]))
        interp[update] = new_val[update]
        if max_change < max_step * 0.1:
            break

    total = int(mask.sum())
    print(f"道路・橋平滑化: {iteration + 1} 回拡散, "
          f"最終変化={max_change:.4f}m, {total} セル対象")

# ---------------------------------------------------------------------------
# JSON 出力
# ---------------------------------------------------------------------------

def save_json(path: str, heightmap: np.ndarray,
              buildingmap: np.ndarray | None,
              surfacemap: np.ndarray | None,
              bridgemap: np.ndarray | None,
              origin_lat: float, origin_lon: float,
              scale: float, base_altitude: float,
              mc_x_start: int, mc_z_start: int,
              centerlinemap: np.ndarray | None = None,
              roadcatmap: np.ndarray | None = None) -> None:
    data = {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "scale": scale,
        "base_altitude": base_altitude,
        "mc_start": {"x": mc_x_start, "z": mc_z_start},
        "size": {"x": int(heightmap.shape[1]), "z": int(heightmap.shape[0])},
        "heightmap": heightmap.tolist(),
    }
    if buildingmap is not None:
        data["buildingmap"] = buildingmap.tolist()
    if surfacemap is not None:
        data["surfacemap"] = surfacemap.tolist()
    if bridgemap is not None:
        data["bridgemap"] = bridgemap.tolist()
    if centerlinemap is not None:
        data["centerlinemap"] = centerlinemap.tolist()
    if roadcatmap is not None:
        data["roadcatmap"] = roadcatmap.tolist()

    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"JSON 保存: {path} ({size_mb:.1f} MB)")

# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    cfg = load_local_config()
    parser = argparse.ArgumentParser(
        description="地理院タイルから Minecraft 地形データを生成する")
    lat_default = cfg.get("lat")
    lon_default = cfg.get("lon")
    parser.add_argument("--lat", type=float,
                        default=lat_default, required=lat_default is None,
                        help="中心緯度")
    parser.add_argument("--lon", type=float,
                        default=lon_default, required=lon_default is None,
                        help="中心経度")
    parser.add_argument("--width", type=int, default=100,
                        help="X方向ブロック数 (default: 100)")
    parser.add_argument("--height", type=int, default=100,
                        help="Z方向ブロック数 (default: 100)")
    parser.add_argument("--base-altitude", type=float, default=0.0,
                        help="基準標高 m (default: 0)")
    parser.add_argument("--scale", type=float, default=0.75,
                        help="m/block (default: 0.75)")
    parser.add_argument("--x-offset", type=int, default=0,
                        help="MC中心の X座標 (default: 0)")
    parser.add_argument("--z-offset", type=int, default=0,
                        help="MC中心の Z座標 (default: 0)")
    parser.add_argument("-o", "--output", default=None,
                        help="出力パス (default: examples/terrain.json)")
    parser.add_argument("--no-fill", action="store_true",
                        help="領域ラベリングをスキップし道路線のみ出力")
    parser.add_argument("--fill", action="store_true",
                        help="rnkWidth=0の道路も領域充填する")
    parser.add_argument("--debug", action="store_true",
                        help="デバッグ用: 道路中心線マップを出力")
    args = parser.parse_args()

    output = args.output or os.path.join(os.path.dirname(__file__), "terrain.json")
    if os.path.isdir(output):
        output = os.path.join(output, "terrain.json")
    scale = args.scale

    # 座標系定数
    m_per_deg_lat = 111_319.0
    m_per_deg_lon = 111_319.0 * math.cos(math.radians(args.lat))
    blocks_per_deg_lat = m_per_deg_lat / scale
    blocks_per_deg_lon = m_per_deg_lon / scale

    mc_x_start = args.x_offset - args.width // 2
    mc_z_start = args.z_offset - args.height // 2

    print(f"中心: ({args.lat}, {args.lon})")
    print(f"範囲: {args.width}×{args.height} ブロック ({scale}m/block)")
    print(f"MC座標: X=[{mc_x_start}, {mc_x_start + args.width}), "
          f"Z=[{mc_z_start}, {mc_z_start + args.height})")

    t0 = time.monotonic()

    # DEM 取得・補間
    interp, dem_x, dem_z, dem_data = fetch_dem(
        args.lat, args.lon, mc_x_start, mc_z_start,
        args.width, args.height, scale,
        blocks_per_deg_lat, blocks_per_deg_lon)

    # ベクトルタイル取得
    road_lines, water_polys, building_polys = fetch_vectors(
        args.lat, args.lon, mc_x_start, mc_z_start,
        args.width, args.height,
        blocks_per_deg_lat, blocks_per_deg_lon)

    # サーフェスマップ・建物マップ・橋マップ生成
    surfacemap, buildingmap, bridgemap, centerlinemap, roadcatmap = gen_maps(
        road_lines, water_polys, building_polys,
        interp.shape, mc_x_start, mc_z_start, scale,
        debug=args.debug, no_fill=args.no_fill, fill=args.fill)

    # 道路平坦化
    flatten_roads(interp, surfacemap, dem_data, dem_x, dem_z,
                  mc_x_start, mc_z_start)

    # 橋の元標高を保存
    bridge_mask = bridgemap.astype(bool) if bridgemap is not None else None
    interp_original_bridge = (interp[bridge_mask].copy()
                              if bridge_mask is not None and bridge_mask.any()
                              else None)

    # 橋セルの高さを隣接道路に合わせる
    adjust_bridge_heights(interp, surfacemap, bridgemap)

    # 道路・橋の段差を平滑化
    smooth_road_bridge(interp, surfacemap, bridgemap, scale)

    # 橋面の高さを bridgemap に記録し、地形用に元の標高を復元
    if bridge_mask is not None and bridge_mask.any():
        bridge_h = np.array([
            [int(round((v - args.base_altitude) / scale * 2)) for v in row]
            for row in interp])
        bridgemap = np.where(bridge_mask, bridge_h, 0).astype(np.int16)
        interp[bridge_mask] = interp_original_bridge

    # heightmap (半ブロック単位)
    h_int = np.array([
        [int(round((v - args.base_altitude) / scale * 2)) for v in row]
        for row in interp])

    # JSON 出力
    save_json(output, h_int, buildingmap, surfacemap, bridgemap,
              args.lat, args.lon, scale, args.base_altitude,
              mc_x_start, mc_z_start, centerlinemap, roadcatmap)

    elapsed = time.monotonic() - t0
    print(f"完了: {elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
