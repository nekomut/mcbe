# pymc

Minecraft Bedrock Edition プロトコルライブラリ for Python.

Bedrock Edition のクライアント・サーバー・プロキシを asyncio ベースで構築できます。

## 特徴

- **asyncio ネイティブ** — 全通信が async/await
- **210 パケット定義** — dataclass + read/write メソッドによる型安全なシリアライズ
- **RakNet 実装** — 自作の非同期 RakNet クライアント/サーバー (UDP)
- **暗号化** — ECDSA P-384 ECDH 鍵交換 + AES-256-CTR パケット暗号化
- **認証** — Microsoft Live OAuth2 → Xbox Live → Minecraft JWT チェーン
- **NBT** — NetworkLittleEndian / LittleEndian / BigEndian の3エンコーディング対応
- **リソースパック** — ZIP/ディレクトリからの読み込み、チャンク分割転送
- **テキスト** — Minecraft カラーコード / ANSI 変換 / HTML タグ変換

## インストール

```bash
pip install pymc

# Realms 接続が必要な場合 (libdatachannel を追加)
pip install pymc[realms]

# 開発用
pip install -e ".[dev]"
```

## クイックスタート

### クライアント

```python
import asyncio
from pymc.dial import Dialer
from pymc.proto.login.data import IdentityData

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
from pymc.listener import ListenConfig, listen

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
from pymc.dial import Dialer
from pymc.raknet import RakNetNetwork
from pymc.proto.login.data import IdentityData

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
        identity_data=IdentityData(display_name="pymc_player"),
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

**クライアント側 (pymc を実行するマシン):**

1. **セキュリティソフト** — セキュリティソフトが UDP をブロックすることがある。ICMP (ping) は通るが UDP が通らない場合はこれが原因
2. **macOS ファイアウォール** — システム設定 → ネットワーク → ファイアウォール が無効か確認
3. **VPN / トンネル** — VPN が LAN 内の UDP 通信を遮断する場合がある。`ifconfig` で `utun` インターフェースを確認

**ネットワーク機器:**

1. **プライバシーセパレーター / 隔離機能** — Wi-Fi ルーターの設定で無線クライアント間通信が許可されているか確認 (Buffalo の場合「プライバシーセパレーター」と「隔離機能」が別設定)
2. 両端末が **同じ SSID / 同じサブネット** に接続されているか確認
3. ルーターの **パケットフィルター** に UDP をブロックするルールがないか確認

**切り分け方法:**

```python
from pymc.raknet import RakNetNetwork
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

### サーバー Ping

```python
import asyncio
from pymc.raknet import RakNetNetwork

async def main():
    network = RakNetNetwork()
    pong = await network.ping("127.0.0.1:19132")
    print(pong.decode())

asyncio.run(main())
```

## プロジェクト構成

```
src/pymc/
├── conn.py              # Connection (バッファリング + 暗号化)
├── dial.py              # Dialer (クライアント接続フロー)
├── listener.py          # Listener (サーバー待受)
├── network.py           # Network ABC + TCP テスト実装
├── auth/                # MS Live / Xbox Live / Minecraft 認証
├── proto/
│   ├── io.py            # PacketReader / PacketWriter
│   ├── types.py         # BlockPos, Vec3, GameRule 等
│   ├── pool.py          # パケットレジストリ + Encoder/Decoder
│   ├── encryption.py    # AES-256-CTR 暗号化
│   ├── login/           # IdentityData, ClientData, JWT
│   └── packet/          # 210 パケット定義
├── raknet/              # 自作 RakNet (UDP)
│   ├── protocol.py      # Frame, ACK/NACK, 定数
│   ├── connection.py    # Client/Server Connection
│   └── network.py       # RakNetNetwork
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

182 テスト: バイナリ IO、NBT、パケットラウンドトリップ、暗号化、接続統合、RakNet プロトコル。

## 依存ライブラリ

| 用途                | パッケージ                                              |
|---------------------|---------------------------------------------------------|
| 暗号化 (ECDSA, AES) | `cryptography`                                          |
| HTTP クライアント   | `aiohttp`                                               |
| JWT                 | `PyJWT`                                                 |
| 圧縮 (flate)        | `zlib` (標準)                                           |
| 圧縮 (snappy)       | `python-snappy` (optional)                              |
| Realms (WebRTC)     | `libdatachannel` (optional, `pip install pymc[realms]`) |

## 謝辞

本プロジェクトは [gophertunnel](https://github.com/sandertv/gophertunnel) (Go) にインスパイアされています。

## ライセンス

MIT
