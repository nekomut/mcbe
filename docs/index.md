# mcbe - Minecraft Bedrock Edition プロトコルライブラリ

**mcbe** は Python の asyncio ベースで Minecraft Bedrock Edition のクライアント・サーバー・プロキシを構築するためのプロトコルライブラリです。

## 特徴

- **asyncio ネイティブ** --- 全通信が async/await で動作
- **212 パケット定義** --- dataclass + read/write メソッドによる型安全なシリアライズ
- **RakNet 実装** --- 自作の非同期 RakNet クライアント/サーバー (UDP)
- **暗号化** --- ECDSA P-384 ECDH 鍵交換 + AES-256-CTR パケット暗号化
- **認証** --- Microsoft Live OAuth2 → Xbox Live → Minecraft JWT チェーン
- **NBT** --- NetworkLittleEndian / LittleEndian / BigEndian の3エンコーディング対応
- **リソースパック** --- ZIP/ディレクトリからの読み込み、チャンク分割転送
- **テキスト** --- Minecraft カラーコード / ANSI 変換 / HTML タグ変換

## ドキュメント

### 基本

- [はじめに (Getting Started)](getting-started.md) --- インストールとクイックスタート
- [アーキテクチャ](architecture.md) --- モジュール構成とパケットパイプライン

### ガイド

- [クライアント接続](guides/client.md) --- BDS/LAN ワールドへの接続
- [サーバー構築](guides/server.md) --- Listener によるサーバー実装
- [Realms 接続](guides/realms.md) --- Realms への認証と接続手順
- [MITM プロキシ](guides/proxy.md) --- パケット解析用プロキシ
- [コマンド実行](guides/commands.md) --- CommandRequest パケットの使い方
- [接続フロー詳細](guides/connection-flow.md) --- BDS / Realms の接続シーケンス比較

## リンク

- [GitHub リポジトリ](https://github.com/) (MIT ライセンス)
- [gophertunnel](https://github.com/sandertv/gophertunnel) --- インスパイア元 (Go 実装)
