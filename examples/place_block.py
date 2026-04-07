"""指定座標にブロックを1つ配置するサンプル.

Usage:
    # BDS に接続して (0, 70, 0) にレッドストーンブロックを配置
    python examples/place_block.py

    # 座標とブロックを指定
    python examples/place_block.py --x 10 --y 64 --z 20 --block diamond_block

    # Realms に接続
    python examples/place_block.py --realms --block gold_block
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from cryptography.hazmat.primitives.asymmetric import ec

from mcbe.dial import Dialer
from mcbe.proto.login.data import IdentityData
from mcbe.proto.packet.command_request import CommandOrigin, CommandRequest, ORIGIN_PLAYER
from mcbe.raknet import RakNetNetwork

logger = logging.getLogger(__name__)


async def resolve_realms(invite_code: str | None = None):
    """Realms に認証して接続情報を返す."""
    from mcbe.auth.live import get_live_token
    from mcbe.auth.xbox import request_xbl_token
    from mcbe.auth.minecraft import request_minecraft_chain

    live_token = await get_live_token()

    # Realms API
    from mcbe.realms import RealmsClient
    xbl_realms = await request_xbl_token(live_token, "https://pocket.realms.minecraft.net/")
    async with RealmsClient(xbl_realms) as client:
        if invite_code:
            realm = await client.realm(invite_code)
        else:
            realms = await client.realms()
            if not realms:
                raise RuntimeError("アクセス可能な Realm がありません")
            realm = realms[0]
        logger.info("Realm: %s (%s)", realm.name, realm.state)
        realm_addr = await realm.address()

    address = realm_addr.address
    is_nethernet = realm_addr.network_protocol and "NETHERNET" in realm_addr.network_protocol.upper()
    is_jsonrpc = is_nethernet and "JSONRPC" in realm_addr.network_protocol.upper()

    key = ec.generate_private_key(ec.SECP384R1())
    network = None
    multiplayer_token = ""

    if is_nethernet:
        from mcbe.auth.service import discover, request_service_token, request_multiplayer_token
        from mcbe.auth.playfab import login_with_xbox as playfab_login
        from mcbe.nethernet import create_network

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
            use_jsonrpc=is_jsonrpc,
        )

    xbl_mp = await request_xbl_token(live_token, "https://multiplayer.minecraft.net/")
    login_chain = await request_minecraft_chain(xbl_mp, key)

    logger.info("Realm アドレス: %s (プロトコル: %s)", address, realm_addr.network_protocol)
    return address, login_chain, key, multiplayer_token, network


async def main(
    address: str, x: int, y: int, z: int, block: str,
    realms: bool = False, invite_code: str | None = None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    login_chain = None
    auth_key = None
    multiplayer_token = ""
    network = None

    if realms:
        logger.info("Realms モード: 認証中...")
        address, login_chain, auth_key, multiplayer_token, network = await resolve_realms(invite_code)
    if network is None:
        network = RakNetNetwork()

    dialer = Dialer(
        identity_data=IdentityData(display_name="mcbe"),
        network=network,
        login_chain=login_chain,
        auth_key=auth_key,
        multiplayer_token=multiplayer_token,
    )

    async with await dialer.dial(address) as conn:
        logger.info("接続完了")

        cmd = f"/setblock {x} {y} {z} {block}"
        await conn.write_packet(CommandRequest(
            command_line=cmd,
            command_origin=CommandOrigin(origin=ORIGIN_PLAYER),
            internal=False,
            version="latest",
        ))
        await conn.flush()
        logger.info("実行: %s", cmd)

        # サーバーからの応答を少し待つ
        await asyncio.sleep(1.0)

    logger.info("完了")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="指定座標にブロックを配置する")
    parser.add_argument("--bds-address", default="127.0.0.1:19132", help="BDS サーバーアドレス (default: 127.0.0.1:19132)")
    parser.add_argument("--x", type=int, default=0, help="X 座標 (default: 0)")
    parser.add_argument("--y", type=int, default=70, help="Y 座標 (default: 70)")
    parser.add_argument("--z", type=int, default=0, help="Z 座標 (default: 0)")
    parser.add_argument("--block", default="redstone_block", help="ブロック ID (default: redstone_block)")
    parser.add_argument("--realms", action="store_true", help="Realms に接続")
    parser.add_argument("--invite-code", help="Realm 招待コード")
    args = parser.parse_args()
    asyncio.run(main(args.bds_address, args.x, args.y, args.z, args.block, realms=args.realms, invite_code=args.invite_code))
