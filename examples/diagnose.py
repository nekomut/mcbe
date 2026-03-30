import argparse
import asyncio
from pymc.raknet import RakNetNetwork


async def diagnose(lan_address: str) -> None:
    network = RakNetNetwork()

    # 公開サーバーへの ping (UDP が外部に通るか確認)
    try:
        pong = await network.ping("play.nethergames.org:19132")
        print(f"External UDP: OK ({pong.decode()[:60]})")
    except Exception:
        print("External UDP: NG (インターネット接続またはUDP全体がブロック)")

    # LAN サーバーへの ping
    try:
        pong = await network.ping(lan_address)
        print(f"LAN UDP: OK ({pong.decode()[:60]})")
    except Exception:
        print("LAN UDP: NG (LAN内のUDPがブロックされている)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UDP connectivity diagnosis")
    parser.add_argument("--address", default="192.168.1.28:19132",
                        help="LAN server address (default: 192.168.1.28:19132)")
    args = parser.parse_args()
    asyncio.run(diagnose(args.address))
