# Listener / listen()

`mcbe.listener` モジュールは、Minecraft Bedrock Edition クライアントからの接続を受け入れるサーバー側の機能を提供する。

---

## ListenConfig クラス

サーバーリスナーの設定を管理するクラス。

```python
ListenConfig(
    *,
    max_players: int = 20,
    authentication_disabled: bool = True,
    compression: int = COMPRESSION_FLATE,
    compression_threshold: int = 256,
    flush_rate: float = 0.05,
    server_name: str = "mcbe Server",
    game_version: str = "1.26.10",
)
```

| フィールド | 型 | デフォルト | 説明 |
|---|---|---|---|
| `max_players` | `int` | `20` | 最大プレイヤー数 |
| `authentication_disabled` | `bool` | `True` | 認証を無効化するか |
| `compression` | `int` | `COMPRESSION_FLATE` | 圧縮アルゴリズム（`COMPRESSION_FLATE` / `COMPRESSION_SNAPPY`） |
| `compression_threshold` | `int` | `256` | 圧縮を適用する最小バイト数 |
| `flush_rate` | `float` | `0.05` | パケットフラッシュ間隔（秒） |
| `server_name` | `str` | `"mcbe Server"` | サーバー名 |
| `game_version` | `str` | `"1.26.10"` | ゲームバージョン文字列 |

---

## listen() 関数

```python
async def listen(
    address: str,
    config: ListenConfig | None = None,
    network: Network | None = None,
) -> Listener
```

Minecraft Bedrock Edition の接続を待ち受けるリスナーを開始する。

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `address` | `str` | (必須) | 待ち受けアドレス（例: `"0.0.0.0:19132"`） |
| `config` | `ListenConfig \| None` | `None` | サーバー設定。`None` の場合はデフォルト値 |
| `network` | `Network \| None` | `None` | ネットワークトランスポート。`None` の場合は `TCPNetwork` |

**戻り値**: 開始済みの `Listener` インスタンス

内部的に ECDSA P-384 秘密鍵を生成し、暗号化ハンドシェイクに使用する。

---

## Listener クラス

接続の受け入れと管理を行うクラス。

### コンストラクタ

```python
Listener(
    network_listener: NetworkListener,
    config: ListenConfig,
    private_key: ec.EllipticCurvePrivateKey,
)
```

通常は `listen()` 関数で生成するため、直接コンストラクタを呼ぶことは少ない。

### メソッド

#### `start()`

```python
async def start() -> None
```

バックグラウンドで接続の受け入れを開始する。`listen()` 関数は内部で自動的にこれを呼び出す。

#### `accept()`

```python
async def accept() -> Connection
```

次の認証済み接続を待ち受けて返す。ハンドシェイクが完了した `Connection` が返される。

#### `close()`

```python
async def close() -> None
```

リスナーを停止し、接続の受け入れを終了する。

---

## 内部ハンドシェイクフロー（サーバー側）

1. **RequestNetworkSettings** 受信 — クライアントのプロトコルバージョンを確認
2. **NetworkSettings** 送信 — 圧縮設定を通知、圧縮を有効化
3. **Login** 受信 — JWT を解析してプレイヤー情報と公開鍵を取得
4. **暗号化** — ECDH で共有シークレットを計算し、ServerToClientHandshake を送信
5. **ClientToServerHandshake** 受信
6. **PlayStatus (LoginSuccess)** 送信
7. **リソースパック交換** — ResourcePacksInfo / ResourcePackStack
8. **ResourcePacksReadyForValidation** 受信 — クライアントのパック検証完了を確認

---

## コード例

```python
import asyncio
from mcbe.listener import listen, ListenConfig
from mcbe.raknet.network import RakNetNetwork

async def main():
    config = ListenConfig(
        server_name="My Server",
        max_players=10,
    )
    listener = await listen(
        "0.0.0.0:19132",
        config=config,
        network=RakNetNetwork(),
    )

    print("サーバー起動中...")
    try:
        conn = await listener.accept()
        print("プレイヤーが接続しました")

        while True:
            pk = await conn.read_packet()
            print(f"受信: {type(pk).__name__}")
    finally:
        await listener.close()

asyncio.run(main())
```
