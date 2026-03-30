"""ブロック配置サンプル.

LAN ワールドに接続し、/setblock コマンドでブロックを配置する。
ワールド側でチートが有効になっている必要がある。

Usage:
    python examples/place_block.py --address 192.168.1.28:19132
"""

from __future__ import annotations

import argparse
import asyncio

from pymc.dial import Dialer
from pymc.raknet import RakNetNetwork
from pymc.proto.login.data import IdentityData
from pymc.proto.packet.command_request import CommandRequest


async def main(address: str) -> None:
    network = RakNetNetwork()

    try:
        pong = await network.ping(address)
        print(f"Server found: {pong.decode()[:80]}")
    except Exception as e:
        print(f"Server not responding: {e}")
        return

    dialer = Dialer(
        identity_data=IdentityData(display_name="pymc_builder"),
        network=network,
    )

    async with await dialer.dial(address) as conn:
        print("Connected!")

        # スポーン完了まで待機
        await asyncio.sleep(2)

        # ブロック配置: /setblock x y z block
        commands = [
            "/setblock 0 4 0 diamond_block",
            "/setblock 1 4 0 gold_block",
            "/setblock 2 4 0 iron_block",
        ]

        for cmd in commands:
            await conn.write_packet(CommandRequest(command_line=cmd))
            print(f"Sent: {cmd}")
            await asyncio.sleep(0.5)

        # レスポンス確認
        for _ in range(20):
            try:
                pk = await asyncio.wait_for(conn.read_packet(), timeout=2.0)
                name = type(pk).__name__
                if name == "CommandOutput":
                    print(f"Response: {pk}")
                elif name == "UpdateBlock":
                    print(f"Block updated: {pk}")
            except asyncio.TimeoutError:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Place blocks via commands")
    parser.add_argument("--address", default="192.168.1.28:19132")
    args = parser.parse_args()
    asyncio.run(main(args.address))
