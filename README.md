# mcbe

Minecraft Bedrock Edition プロトコルライブラリ for Python.

Bedrock Edition のクライアント・サーバー・プロキシを asyncio ベースで構築できます。

## 特徴

- **asyncio ネイティブ** — 全通信が async/await
- **212 パケット定義** — dataclass + read/write メソッドによる型安全なシリアライズ
- **RakNet 実装** — 自作の非同期 RakNet クライアント/サーバー (UDP)
- **暗号化** — ECDSA P-384 ECDH 鍵交換 + AES-256-CTR パケット暗号化
- **認証** — Microsoft Live OAuth2 → Xbox Live → Minecraft JWT チェーン
- **NBT** — NetworkLittleEndian / LittleEndian / BigEndian の3エンコーディング対応
- **リソースパック** — ZIP/ディレクトリからの読み込み、チャンク分割転送
- **テキスト** — Minecraft カラーコード / ANSI 変換 / HTML タグ変換
- **Realms (NetherNet)** — WebRTC DataChannel 経由の Realms 接続 (libdatachannel / aiortc 両対応)

## インストール

```bash
pip install mcbe

# C++ ネイティブ WebRTC バックエンドを追加 (Realms 接続が高速・安定)
pip install mcbe[libdatachannel]

# 開発用
pip install -e ".[dev]"
```

> **Note:** `pip install mcbe` だけで Realms 接続可能です（aiortc 同梱）。
> aiortc は BDS 互換性のためモンキーパッチを適用しています（SCTP ストリーム数、max-message-size、TURN TLS、RFC 8489 STUN 修正など）。
> aiortc のバージョンアップでパッチが動作しなくなる可能性があるため、
> **安定した Realms 接続には `pip install mcbe[libdatachannel]`** を推奨します（C++ ネイティブ実装、自動的に優先使用）。

## クイックスタート

### クライアント

```python
import asyncio
from mcbe.dial import Dialer
from mcbe.proto.login.data import IdentityData

async def main():
    dialer = Dialer(
        identity_data=IdentityData(display_name="Steve"),
    )
    async with await dialer.dial("127.0.0.1:19132") as conn:
        print("Connected!")
        while not conn.closed:
            pk = await conn.read_packet()
            print(f"Received: {type(pk).__name__}")

asyncio.run(main())
```

### サーバー

```python
import asyncio
from mcbe.listener import ListenConfig, listen

async def main():
    config = ListenConfig(
        server_name="My Server",
        authentication_disabled=True,
    )
    server = await listen("0.0.0.0:19132", config=config)
    print("Listening...")
    conn = await server.accept()
    print("Player connected!")
    # パケットの読み書き...

asyncio.run(main())
```

### MITM プロキシ

```bash
python examples/proxy.py --listen 0.0.0.0:19133 --remote 127.0.0.1:19132
```

### ローカルネットワーク上のワールドに接続する

LAN 上で「マルチプレイヤーに公開」されているワールドに接続するには、`RakNetNetwork` を Dialer に渡します。
Minecraft Bedrock Edition は RakNet (UDP) で通信するため、TCP ではなく RakNet トランスポートが必要です。

```python
import asyncio
from mcbe.dial import Dialer
from mcbe.raknet import RakNetNetwork
from mcbe.proto.login.data import IdentityData

async def main():
    # 1. RakNet で LAN サーバーを Ping して存在確認 (任意)
    network = RakNetNetwork()
    try:
        pong = await network.ping("192.168.1.10:19132")
        print(f"Server found: {pong.decode()}")
    except Exception as e:
        print(f"Server not responding: {e}")
        return

    # 2. RakNetNetwork を指定して接続
    dialer = Dialer(
        identity_data=IdentityData(display_name="mcbe_player"),
        network=network,
    )
    async with await dialer.dial("192.168.1.10:19132") as conn:
        print("Connected to LAN world!")
        while not conn.closed:
            pk = await conn.read_packet()
            print(f"Received: {type(pk).__name__}")

asyncio.run(main())
```

**接続先アドレスの確認方法:**

- ワールドを開いているデバイスの **ローカル IP アドレス** (例: `192.168.1.10`) を使用
- ポートはデフォルト `19132`。Minecraft の設定画面で確認可能
- ワールド側で **設定 → マルチプレイヤー → 「LAN プレイヤーに表示」** を有効にしておく必要あり

**注意事項:**

- LAN ワールドは認証なし (オフラインモード) で接続可能。Dialer はデフォルトで自己署名 JWT を生成する
- Xbox Live 認証が必要なサーバーに接続する場合は、`auth/` モジュールで取得したトークンを Dialer に設定する

### LAN 接続のトラブルシューティング

RakNet は **UDP** で通信します。LAN ワールドに接続できない場合、以下を順に確認してください。

**ホスト側 (ワールドを開いている端末):**

1. ワールド内にいる状態で **設定 → マルチプレイヤー** を開く
2. **「マルチプレイヤーゲーム」** と **「LAN プレイヤーに表示」** が両方 ON
3. **Microsoft アカウントにサインイン済み** (未サインインだと LAN 公開が実際には機能しない)
4. iOS の場合: **設定アプリ → Minecraft → 「ローカルネットワーク」が ON** (iOS 14 以降必須)
5. アプリが**フォアグラウンド**にあること (バックグラウンドではネットワーク通信が停止する)

**クライアント側 (mcbe を実行するマシン):**

1. **セキュリティソフト** — セキュリティソフトが UDP をブロックすることがある。ICMP (ping) は通るが UDP が通らない場合はこれが原因
2. **macOS ファイアウォール** — システム設定 → ネットワーク → ファイアウォール が無効か確認
3. **VPN / トンネル** — VPN が LAN 内の UDP 通信を遮断する場合がある。`ifconfig` で `utun` インターフェースを確認

**ネットワーク機器:**

1. **プライバシーセパレーター / 隔離機能** — Wi-Fi ルーターの設定で無線クライアント間通信が許可されているか確認 (Buffalo の場合「プライバシーセパレーター」と「隔離機能」が別設定)
2. 両端末が **同じ SSID / 同じサブネット** に接続されているか確認
3. ルーターの **パケットフィルター** に UDP をブロックするルールがないか確認

**切り分け方法:**

```python
from mcbe.raknet import RakNetNetwork
import asyncio

async def diagnose():
    network = RakNetNetwork()

    # 公開サーバーへの ping (UDP が外部に通るか確認)
    try:
        pong = await network.ping("play.nethergames.org:19132")
        print(f"External UDP: OK ({pong.decode()[:60]})")
    except Exception:
        print("External UDP: NG (インターネット接続またはUDP全体がブロック)")

    # LAN サーバーへの ping
    try:
        pong = await network.ping("192.168.1.10:19132")
        print(f"LAN UDP: OK ({pong.decode()[:60]})")
    except Exception:
        print("LAN UDP: NG (LAN内のUDPがブロックされている)")

asyncio.run(diagnose())
```

- **External OK / LAN NG** → セキュリティソフトまたはルーターが LAN 内 UDP をブロック
- **両方 NG** → UDP 自体がブロックされている (VPN やファイアウォール)
- **両方 OK** → Minecraft ホスト側の設定を確認

### Realms に接続してコマンドを実行する

Realms への接続には Microsoft / Xbox Live / PlayFab 認証と WebRTC (NetherNet) が必要です。
`examples/place_block.py` がフルフローの参考になります。

```python
import asyncio
from cryptography.hazmat.primitives.asymmetric import ec

from mcbe.auth.live import get_live_token
from mcbe.auth.xbox import request_xbl_token
from mcbe.auth.minecraft import request_minecraft_chain
from mcbe.auth.service import discover, request_service_token, request_multiplayer_token
from mcbe.auth.playfab import login_with_xbox as playfab_login
from mcbe.nethernet import create_network
from mcbe.realms import RealmsClient
from mcbe.dial import Dialer
from mcbe.proto.login.data import IdentityData
from mcbe.proto.packet.command_request import CommandOrigin, CommandRequest, ORIGIN_PLAYER

async def main():
    live_token = await get_live_token()
    key = ec.generate_private_key(ec.SECP384R1())

    # Realms API で接続先を取得
    xbl_realms = await request_xbl_token(live_token, "https://pocket.realms.minecraft.net/")
    async with RealmsClient(xbl_realms) as client:
        realms = await client.realms()
        realm = realms[0]
        realm_addr = await realm.address()

    # NetherNet 認証
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
        use_jsonrpc=True,
    )

    # Minecraft ログインチェーン
    xbl_mp = await request_xbl_token(live_token, "https://multiplayer.minecraft.net/")
    login_chain = await request_minecraft_chain(xbl_mp, key)

    # 接続
    dialer = Dialer(
        identity_data=IdentityData(display_name="mcbe"),
        network=network, login_chain=login_chain,
        auth_key=key, multiplayer_token=multiplayer_token,
    )
    async with await dialer.dial(realm_addr.address) as conn:
        await conn.write_packet(CommandRequest(
            command_line="/setblock 0 70 0 diamond_block",
            command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
            internal=False,
        ))
        await conn.flush()
        await asyncio.sleep(1.0)

asyncio.run(main())
```

**WebRTC バックエンド:**

| バックエンド | インストール | 特徴 |
|-------------|------------|------|
| libdatachannel | `pip install mcbe[libdatachannel]` | C++ ネイティブ。安定・高速。自動的に優先使用 |
| aiortc | `pip install mcbe` (同梱) | 純 Python。BDS 互換パッチを自動適用 |

`create_network(backend="aiortc")` のように明示指定も可能。

### サーバー Ping

```python
import asyncio
from mcbe.raknet import RakNetNetwork

async def main():
    network = RakNetNetwork()
    pong = await network.ping("127.0.0.1:19132")
    print(pong.decode())

asyncio.run(main())
```

## プロジェクト構成

```
src/mcbe/
├── conn.py              # Connection (バッファリング + 暗号化)
├── dial.py              # Dialer (クライアント接続フロー)
├── listener.py          # Listener (サーバー待受)
├── network.py           # Network ABC + TCP テスト実装
├── auth/                # MS Live / Xbox Live / Minecraft / PlayFab / Service 認証
├── proto/
│   ├── io.py            # PacketReader / PacketWriter
│   ├── types.py         # BlockPos, Vec3, GameRule 等
│   ├── pool.py          # パケットレジストリ + Encoder/Decoder
│   ├── encryption.py    # AES-256-CTR 暗号化
│   ├── login/           # IdentityData, ClientData, JWT
│   └── packet/          # 212 パケット定義
├── raknet/              # 自作 RakNet (UDP)
│   ├── protocol.py      # Frame, ACK/NACK, 定数
│   ├── connection.py    # Client/Server Connection
│   └── network.py       # RakNetNetwork
├── nethernet/           # WebRTC (NetherNet) for Realms
│   ├── __init__.py      # create_network() — バックエンド自動選択
│   ├── network.py       # aiortc バックエンド (TURN TLS 対応)
│   ├── ldc_network.py   # libdatachannel バックエンド
│   ├── conn.py          # NetherNet Connection (セグメント再構成)
│   ├── signaling.py     # WebSocket / JSON-RPC シグナリング
│   └── aiortc_patch.py  # aiortc/aioice 互換パッチ (SCTP, TURN, RFC 8489)
├── realms/              # Realms API クライアント
├── nbt/                 # NBT エンコード/デコード
├── resource/            # リソースパック
├── text/                # カラーコード処理
└── query/               # UT3 クエリプロトコル
```

## テスト

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

196 テスト: バイナリ IO、NBT、パケットラウンドトリップ、暗号化、接続統合、RakNet プロトコル、チャンクパーサ。

## サンプル

`examples/` ディレクトリにユースケース別のサンプルがあります:

| ファイル | 説明 |
|---------|------|
| `client.py` | BDS への基本的な接続 |
| `conn_lan_host.py` | LAN ワールドへの接続 |
| `get_block.py` | 指定座標のブロック情報を取得 |
| `place_block.py` | BDS / Realms にブロックを配置 |
| `list_realms.py` | Realms への接続 |
| `proxy.py` | MITM プロキシ |
| `terrain_gen.py` | 地形データ生成 |
| `terrain_build.py` | 生成した地形データの配置 |
| `map.py` | マップ可視化 (HTML 出力) |
| `diagnose.py` | ネットワーク診断 |

## 依存ライブラリ

| 用途                | パッケージ                                              |
|---------------------|---------------------------------------------------------|
| 暗号化 (ECDSA, AES) | `cryptography`                                          |
| HTTP クライアント   | `aiohttp`                                               |
| JWT                 | `PyJWT`                                                 |
| WebSocket           | `websockets`                                            |
| 圧縮 (flate)        | `zlib` (標準)                                           |
| 圧縮 (snappy)       | `python-snappy` (optional)                              |
| Realms (WebRTC)     | `aiortc` (同梱)、`libdatachannel` (optional, 推奨)       |

## 謝辞

本プロジェクトは [gophertunnel](https://github.com/sandertv/gophertunnel) (Go) にインスパイアされています。

## ライセンス

MIT
