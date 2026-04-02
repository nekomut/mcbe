"""地理院タイルから Minecraft 地形データを生成する.

DEM5A 標高タイル（txt）+ ベクトルタイル（pbf）から terrain.json を出力。
GML ファイル不要。緯度経度を指定するだけで任意の場所の地形を生成できる。
出力は place_block.py と互換。

Usage:
    python examples/gen_terrain.py --lat 36.104665 --lon 140.087099
    python examples/gen_terrain.py --lat 35.6895 --lon 139.6917 --width 500 --height 500
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
ROAD_EDGE_CODES = {2701, 2703, 2704, 2711, 2721, 2723, 2731}
# z=16 の ftCode 22xx は名目上「中心線」だが実際は縁線の近くを走る → 追加縁線として扱う
ROAD_EXTRA_EDGE_CODES = {2201, 2221}

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


def fetch_url(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception:
        return None

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

    margin = 0.002
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

    margin = 0.001
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

    road_lines: list[tuple[list, int]] = []
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

    # z=15: 道路縁線
    for layer_name, geom, props in feats_z15:
        if layer_name == "road":
            ft = props.get("ftCode", 0)
            if ft not in ROAD_EDGE_CODES:
                continue
            for line in extract_lines(geom):
                road_lines.append((line, ft))
        elif layer_name == "waterarea":
            water_polys.extend(extract_polys(geom))
        elif layer_name == "building":
            building_polys.extend(extract_polys(geom))

    z15_count = len(road_lines)

    # z=16: 追加縁線（22xx=名目上中心線だが実質縁線 + 27xx=縁線）
    z16_valid = ROAD_EDGE_CODES | ROAD_EXTRA_EDGE_CODES
    for layer_name, geom, props in feats_z16:
        if layer_name == "road":
            ft = props.get("ftCode", 0)
            if ft not in z16_valid:
                continue
            for line in extract_lines(geom):
                road_lines.append((line, ft))

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
             scale: float, *, debug: bool = False,
             ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    """道路・水域・建物からサーフェスマップ・建物マップ・橋マップを生成.

    Returns: (surfacemap, buildingmap, bridgemap, centerlinemap)
        centerlinemap: debug=True のとき、道路中心線の boolean マップ (int8)。
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

    # --- 道路 (Voronoi 法) ---
    # 1) z=15 縁線をまずラスタライズ
    # 2) z=16 追加縁線は z=15 縁線の近傍にあるもののみ採用
    #    (孤立した z=16 線が遠方の z=15 線と誤ペアリングするのを防ぐ)
    label_map = np.zeros(shape, dtype=np.int32)
    label_id = 0
    max_road_half_width = 5.0 / scale

    def rasterize_line(mc_coords, lid):
        """線分を label_map にラスタライズ。描画したピクセル数を返す."""
        count = 0
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
                    label_map[iz, ix] = lid
                    count += 1
        return count

    # Pass 1: z=15 縁線
    z15_count = 0
    for mc_coords, ft_code in road_lines:
        if ft_code in ROAD_EXTRA_EDGE_CODES:
            continue
        label_id += 1
        rasterize_line(mc_coords, label_id)
        z15_count += 1

    # z=15 縁線からの距離を計算
    z15_edge = label_map > 0
    if z15_edge.any():
        z15_dist = distance_transform_edt(~z15_edge)
    else:
        z15_dist = np.full(shape, np.inf)

    # Pass 2: z=16 追加縁線（z=15 縁線の近傍にあるもののみ）
    # 同時に center_mask にもラスタライズ（debug 用中心線表示）
    center_mask = np.zeros(shape, dtype=bool)
    z16_count = 0
    z16_skip = 0
    for mc_coords, ft_code in road_lines:
        if ft_code not in ROAD_EXTRA_EDGE_CODES:
            continue
        # この線の各頂点が z=15 縁線から近いか判定
        close = False
        for x, z in mc_coords:
            ix = int(round(x - mc_x_start))
            iz = int(round(z - mc_z_start))
            if 0 <= ix < nx and 0 <= iz < ny:
                if z15_dist[iz, ix] <= max_road_half_width:
                    close = True
                    break
        if not close:
            z16_skip += 1
            continue
        label_id += 1
        rasterize_line(mc_coords, label_id)
        # center_mask にもラスタライズ
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
                cix = int(round(ix0 + t * (ix1 - ix0)))
                ciz = int(round(iz0 + t * (iz1 - iz0)))
                if 0 <= cix < nx and 0 <= ciz < ny:
                    center_mask[ciz, cix] = True
        z16_count += 1

    print(f"  道路縁線: z15={z15_count}, z16={z16_count} 採用, "
          f"{z16_skip} 除外 (計 {label_id} ラベル)")

    # 除外マスク
    exclude = water_mask.copy()
    if buildingmap is not None:
        exclude |= buildingmap.astype(bool)

    edge_mask = label_map > 0
    bridge_mask = np.zeros(shape, dtype=bool)
    road_filled = np.zeros(shape, dtype=bool)
    voronoi_bnd = np.zeros(shape, dtype=bool)

    # Voronoi 法で縁線間を充填
    if edge_mask.any():
        dist1, idx1 = distance_transform_edt(
            ~edge_mask, return_distances=True, return_indices=True)
        nearest_label = label_map[idx1[0], idx1[1]]

        for dz, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nz_ = np.clip(np.arange(ny)[:, None] + dz, 0, ny - 1)
            nx_ = np.clip(np.arange(nx)[None, :] + dx, 0, nx - 1)
            neighbor_label = nearest_label[nz_, nx_]
            neighbor_dist = dist1[nz_, nx_]
            diff = ((nearest_label != neighbor_label)
                    & (nearest_label > 0) & (neighbor_label > 0)
                    & (dist1 <= max_road_half_width)
                    & (neighbor_dist <= max_road_half_width))
            voronoi_bnd |= diff

        road_filled = edge_mask.copy()
        if voronoi_bnd.any():
            dist_to_bnd, bnd_idx = distance_transform_edt(
                ~voronoi_bnd, return_distances=True, return_indices=True)
            local_half_width = dist1[bnd_idx[0], bnd_idx[1]]
            local_half_width = np.minimum(local_half_width, max_road_half_width)
            road_filled = ((dist1 + dist_to_bnd <= local_half_width + 1.5)
                           & (dist1 <= max_road_half_width))
            road_filled |= edge_mask

            # --- 交差点充填（Voronoi 三重点検出）---
            # 道路近傍で非道路のギャップを連結成分分析し、
            # 3+ の異なるラベルが集まる領域を交差点として充填する
            gap = (dist1 <= max_road_half_width * 2) & ~road_filled
            gap_labeled, n_gap = ndimage_label(gap)
            intersection_count = 0
            for comp_id in range(1, n_gap + 1):
                comp_mask = gap_labeled == comp_id
                labels_in_comp = np.unique(nearest_label[comp_mask])
                labels_in_comp = labels_in_comp[labels_in_comp > 0]
                if len(labels_in_comp) >= 3:
                    road_filled[comp_mask] = True
                    intersection_count += 1
            print(f"  交差点: {intersection_count} 箇所充填")

    if road_filled.any():
        # 橋 = 道路が水域を横断する箇所
        bridge_seed = road_filled & water_mask
        if bridge_seed.any() and edge_mask.any():
            # 水岸の道路縁線から橋幅を決定する:
            # 水域に隣接する陸上の道路セル（岸）の道路半幅を取得し、
            # 橋の各セルに最寄りの岸の半幅を適用する。
            shore_road = road_filled & ~water_mask  # 陸上の道路
            if shore_road.any():
                # 各セルから最寄りの岸道路セルまでの距離・インデックス
                shore_dist, shore_idx = distance_transform_edt(
                    ~shore_road, return_distances=True, return_indices=True)
                # 岸道路セルでの dist1（最寄り縁線までの距離）= 道路半幅
                shore_hw = dist1[shore_idx[0], shore_idx[1]]
                shore_hw = np.minimum(shore_hw, max_road_half_width)
                # 橋の細い線から膨張（各セルの半幅は岸の道路幅に従う）
                bridge_dist = distance_transform_edt(~bridge_seed)
                bridge_mask = water_mask & (bridge_dist <= shore_hw)
            else:
                bridge_mask = bridge_seed
        else:
            bridge_mask = bridge_seed if road_filled.any() else np.zeros(shape, dtype=bool)
        if buildingmap is not None:
            bridge_mask &= ~buildingmap.astype(bool)
        surface[road_filled & ~exclude] = SURFACE_ROAD

    road_count = int((surface == SURFACE_ROAD).sum())
    bridge_count = int(bridge_mask.sum())
    grass_count = int((surface == SURFACE_GRASS).sum())
    print(f"道路セル: {road_count}/{ny * nx}")
    print(f"橋セル: {bridge_count}/{ny * nx}")
    print(f"草地セル: {grass_count}/{ny * nx}")

    bridgemap = bridge_mask.astype(np.int8) if bridge_count > 0 else None

    # 中心線マップ (debug 用): z=16 中心線は全て維持
    centerlinemap = None
    if debug:
        road_or_bridge = (surface == SURFACE_ROAD) | bridge_mask
        cl = center_mask & road_or_bridge
        centerlinemap = cl.astype(np.int8)
        print(f"中心線セル: {int(cl.sum())}/{ny * nx}")

    return surface, buildingmap, bridgemap, centerlinemap

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
              centerlinemap: np.ndarray | None = None) -> None:
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

    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"JSON 保存: {path} ({size_mb:.1f} MB)")

# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="地理院タイルから Minecraft 地形データを生成する")
    parser.add_argument("--lat", type=float, required=True, help="中心緯度")
    parser.add_argument("--lon", type=float, required=True, help="中心経度")
    parser.add_argument("--width", type=int, default=300,
                        help="X方向ブロック数 (default: 300)")
    parser.add_argument("--height", type=int, default=300,
                        help="Z方向ブロック数 (default: 300)")
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
    surfacemap, buildingmap, bridgemap, centerlinemap = gen_maps(
        road_lines, water_polys, building_polys,
        interp.shape, mc_x_start, mc_z_start, scale, debug=args.debug)

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
              mc_x_start, mc_z_start, centerlinemap)

    elapsed = time.monotonic() - t0
    print(f"完了: {elapsed:.1f} 秒")


if __name__ == "__main__":
    main()
