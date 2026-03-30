#!/usr/bin/env python3
"""Simple client example for Minecraft Bedrock Edition.

Connects to a server, completes the login handshake, and reads packets.

Usage:
    python examples/client.py --address 127.0.0.1:19132
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pymc.dial import Dialer
from pymc.proto.login.data import IdentityData
from pymc.proto.pool import UnknownPacket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("client")


async def run_client(address: str, player_name: str) -> None:
    """Connect to a server and read packets."""
    dialer = Dialer(
        identity_data=IdentityData(
            display_name=player_name,
        ),
    )

    logger.info("Connecting to %s as %s...", address, player_name)

    async with await dialer.dial(address) as conn:
        logger.info("Connected and spawned!")

        # Read and log packets.
        while not conn.closed:
            try:
                pk = await asyncio.wait_for(conn.read_packet(), timeout=30.0)
                name = type(pk).__name__
                if isinstance(pk, UnknownPacket):
                    name = f"Unknown(0x{pk.packet_id:02x}, {len(pk.payload)} bytes)"
                logger.info("Received: %s", name)
            except asyncio.TimeoutError:
                logger.info("No packets for 30s, disconnecting")
                break
            except Exception as e:
                logger.error("Error: %s", e)
                break


def main():
    parser = argparse.ArgumentParser(description="Minecraft Bedrock Client")
    parser.add_argument(
        "--address", default="127.0.0.1:19132",
        help="Server address (default: 127.0.0.1:19132)",
    )
    parser.add_argument(
        "--name", default="pymc_player",
        help="Player name (default: pymc_player)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_client(args.address, args.name))
    except KeyboardInterrupt:
        logger.info("Disconnected")


if __name__ == "__main__":
    main()
