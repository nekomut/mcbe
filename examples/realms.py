import asyncio
from pymc.auth.live import request_live_token
from pymc.auth.xbox import request_xbl_token
from pymc.realms import RealmsClient

async def main():
    # 1. 認証
    live_token = await request_live_token()
    xbl_token = await request_xbl_token(
        live_token,
        "https://pocket.realms.minecraft.net/",
    )

    # 2. Realms API
    async with RealmsClient(xbl_token) as client:
        realms = await client.realms()
        for i, realm in enumerate(realms):
            print(f"[{i}] {realm.name} ({realm.state})")

        if not realms:
            print("アクセス可能な Realm がありません")
            return

        # 最初の Realm に接続
        realm = realms[0]
        print(f"\n{realm.name} のアドレスを取得中...")
        addr = await realm.address()
        print(f"Connect to: {addr}")

asyncio.run(main())
