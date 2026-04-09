# アーキテクチャ

## モジュール依存関係

```
                    ┌───────────┐
                    │  dial.py  │  クライアント接続 (Dialer)
                    │listener.py│  サーバー待受 (Listener)
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │  conn.py  │  Connection (バッファリング + 暗号化)
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │ network.py│  Network ABC (トランスポート抽象化)
                    └─────┬─────┘
                          │
              ┌───────────┼───────────┐
              │                       │
        ┌─────▼─────┐          ┌─────▼─────┐
        │  raknet/   │          │ nethernet/ │
        │ (UDP)      │          │ (WebRTC)   │
        └────────────┘          └────────────┘

    ┌──────────────────────────────────────────┐
    │                proto/                     │
    │  io.py       PacketReader / PacketWriter  │
    │  types.py    BlockPos, Vec3, GameRule 等   │
    │  pool.py     パケットレジストリ + Encoder  │
    │  encryption.py  AES-256-CTR 暗号化        │
    │  login/      IdentityData, ClientData, JWT│
    │  packet/     214 パケット定義               │
    └──────────────────────────────────────────┘

    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  auth/   │  │   nbt/   │  │ resource/ │  │ chunk.py │
    │ MS/Xbox  │  │ NBT codec│  │ リソース  │  │ SubChunk │
    │ 認証     │  │          │  │ パック    │  │ パーサ   │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

## 主要モジュール

### `dial.py` - Dialer

クライアント接続を行う。`Dialer.dial(address)` を呼ぶと、トランスポート接続からログインハンドシェイク、リソースパックネゴシエーション、スポーンまでを一括で処理し、使用可能な `Connection` を返す。

主なパラメータ:

- `identity_data` --- プレイヤー名、UUID、XUID
- `client_data` --- クライアントデバイス情報
- `network` --- トランスポート層 (`RakNetNetwork`, `create_network()` 等)
- `login_chain` --- 認証済み JWT チェーン (Realms 用)
- `auth_key` --- 認証鍵 (Realms 用)
- `multiplayer_token` --- マルチプレイヤートークン (Realms 用)

### `listener.py` - Listener

サーバー側の接続受け入れを行う。`listen(address, config)` で起動し、`Listener.accept()` で接続を待つ。

### `conn.py` - Connection

パケットの読み書きを抽象化する。以下の機能を持つ:

- パケットのバッファリングとフラッシュ
- 圧縮 (flate / snappy)
- 暗号化 (AES-256-CTR)
- コンテキストマネージャ (`async with`) 対応

### `network.py` - Network ABC

トランスポート層の抽象インターフェース。`connect()` (クライアント)、`listen()` (サーバー)、`ping()` を定義する。

## トランスポート層

| 種類 | プロトコル | 用途 | クラス |
|------|-----------|------|--------|
| RakNet | UDP | BDS / LAN ワールド | `RakNetNetwork` |
| NetherNet | WebRTC (DTLS/SCTP DataChannel) | Realms | `create_network()` |
| TCP | TCP | テスト用 | `TCPNetwork` |

### RakNet (BDS / LAN)

`raknet/` パッケージに自作の非同期 RakNet 実装がある。MTU ネゴシエーション、フレーム分割/再構築、ACK/NACK による信頼性を提供する。

### NetherNet (Realms)

`nethernet/` パッケージが WebRTC DataChannel を使った接続を提供する。バックエンドは libdatachannel (C++ ネイティブ) または aiortc (Pure Python) を選択可能。

## パケットパイプライン

### エンコード (送信)

```
Packet (dataclass)
  → encode_packet()    # パケットIDヘッダ + バイナリシリアライズ
  → encode_batch()     # 圧縮 (flate/snappy) + バッチヘッダ (0xFE)
  → encrypt()          # AES-256-CTR 暗号化 (有効時)
  → Transport          # RakNet / NetherNet / TCP
```

### デコード (受信)

```
Transport
  → decrypt()          # AES-256-CTR 復号 (有効時)
  → decode_batch()     # バッチヘッダ除去 + 解凍
  → decode_packet()    # パケットID判定 + デシリアライズ
  → Packet (dataclass)
```

> **NetherNet の場合:** バッチヘッダ (0xFE) は付与されず、Minecraft 層の暗号化も無効 (DTLS がトランスポート層で暗号化を担当)。

## チャンク解析 (`chunk.py`)

SubChunk パケットのバイナリデータからブロック情報を抽出するモジュール。

- **`parse_sub_chunk_entries()`** --- SubChunkResponse のバイナリエントリを解析し、各サブチャンクのブロックストレージ (4096 ブロック) を返す。HeightMap / RenderHeightMap の読み飛ばしも処理
- **`parse_sub_chunk()`** --- 単一サブチャンクデータ (Version 8/9) をパースし、ブロックランタイム ID 配列を返す
- **`parse_level_chunk_top_blocks()`** --- LevelChunk パケットから各カラムの最上面ブロックを抽出
- **`compute_block_hash()`** --- ブロック名 + 状態から FNV-1a ハッシュを計算 (canonical_block_states.nbt との照合用)

`data/canonical_block_states.nbt` にプロトコルバージョン対応の全ブロック状態定義を格納している。

## プロトコルフロー概要

1. **トランスポート接続** --- RakNet MTU ネゴシエーション or WebRTC シグナリング
2. **RequestNetworkSettings / NetworkSettings** --- 圧縮設定の交換
3. **Login** --- JWT による認証 (オフライン: 自己署名、Realms: Xbox Live 認証チェーン)
4. **暗号化ハンドシェイク** --- ServerToClientHandshake / ClientToServerHandshake (ECDH 鍵交換)
5. **リソースパックネゴシエーション** --- ResourcePacksInfo → Response → Stack → Completed
6. **ゲーム開始** --- StartGame → RequestChunkRadius → ChunkRadiusUpdated → PlayStatus(PlayerSpawn)

詳細は [接続フロー詳細](guides/connection-flow.md) を参照。
