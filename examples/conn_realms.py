import asyncio
from pymc.auth.live import get_live_token
from pymc.auth.xbox import request_xbl_token
from pymc.realms import RealmsClient

async def main():
    # 1. 認証（キャッシュ付き）
    live_token = await get_live_token()
    xbl_token = await request_xbl_token(
        live_token,
        "https://pocket.realms.minecraft.net/",
    )

    # 2. Realms API
    async with RealmsClient(xbl_token) as client:
        realms = await client.realms()
        if not realms:
            print("アクセス可能な Realm がありません")
            return

        for i, realm in enumerate(realms):
            print(f"[{i}] {realm.name}")
            print(f"    ID: {realm.id}  状態: {realm.state}")
            print(f"    オーナー: {realm.owner}  プレイヤー: {len(realm.players)}/{realm.max_players}")
            print(f"    残り日数: {realm.days_left}  期限切れ: {realm.expired}")
            if realm.motd:
                print(f"    MOTD: {realm.motd}")

        # 最初の Realm に接続
        realm = realms[0]
        print(f"\n{realm.name} のアドレスを取得中...")
        addr = await realm.address()
        print(f"プロトコル: {addr.network_protocol}")
        print(f"アドレス: {addr.address}")

asyncio.run(main())
