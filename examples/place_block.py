"""ブロック配置ボット.

BDS に直接接続し、/setblock コマンドでブロックを配置する。
mc/samples/golang/blockplacer2 の Python 移植版。

初回のみ BDS コンソールで /op bot を実行すること。

Usage:
    python examples/place_block.py --address 192.168.1.28:19132
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from pymc.dial import Dialer
from pymc.raknet import RakNetNetwork
from pymc.proto.login.data import IdentityData
from pymc.proto.packet.command_request import CommandOrigin, CommandRequest, ORIGIN_PLAYER
from pymc.proto.packet.network_stack_latency import NetworkStackLatency

logger = logging.getLogger(__name__)

WAIT_TIME = 30  # seconds


async def main(address: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    network = RakNetNetwork()

    try:
        pong = await network.ping(address)
        logger.info("サーバー発見: %s", pong.decode()[:80])
    except Exception as e:
        logger.error("サーバー応答なし: %s", e)
        return

    logger.info("BDS %s に直接接続します...", address)

    dialer = Dialer(
        identity_data=IdentityData(
            display_name="bot",
            identity="b1e3a2f4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
            xuid="1000000000000000",
        ),
        network=network,
    )

    conn = await dialer.dial(address)
    logger.info("スポーン完了!")
    logger.info("初回のみ BDS コンソールで /op bot を実行してください")
    logger.info("%d秒後にブロック配置を開始します...", WAIT_TIME)

    # パケット読み取りタスク（接続維持 + コマンド結果表示）
    async def read_packets() -> None:
        try:
            while True:
                pk = await conn.read_packet()
                if isinstance(pk, NetworkStackLatency):
                    if pk.needs_response:
                        await conn.write_packet(
                            NetworkStackLatency(
                                timestamp=pk.timestamp,
                                needs_response=False,
                            )
                        )
                        await conn.flush()
                else:
                    name = type(pk).__name__
                    if name == "UnknownPacket":
                        continue
                    logger.debug("受信: %s", name)
        except Exception as e:
            logger.debug("パケット読み取り終了: %s", e)

    read_task = asyncio.create_task(read_packets())

    try:
        await asyncio.sleep(WAIT_TIME)

        logger.info("=== ブロック配置開始 (Y=70〜80) ===")
        for y in range(70, 81):
            cmd = f"/setblock 0 {y} 0 stone"
            logger.info("[配置] %s", cmd)

            await conn.write_packet(
                CommandRequest(
                    command_line=cmd,
                    command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
                    internal=False,
                    version="latest",
                )
            )
            await conn.flush()
            await asyncio.sleep(0.2)

        logger.info("=== ブロック配置完了! ===")

        # コマンド応答を待つ
        await asyncio.sleep(5)

    finally:
        read_task.cancel()
        try:
            await read_task
        except asyncio.CancelledError:
            pass
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Place blocks via commands")
    parser.add_argument("--address", default="192.168.1.28:19132")
    args = parser.parse_args()
    asyncio.run(main(args.address))
