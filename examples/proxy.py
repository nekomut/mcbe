#!/usr/bin/env python3
"""MITM Proxy example for Minecraft Bedrock Edition.

This proxy sits between a Minecraft client and server, forwarding all
packets while logging them. Useful for protocol analysis and debugging.

Usage:
    python examples/proxy.py --listen 0.0.0.0:19133 --remote 127.0.0.1:19132

The client connects to the proxy (port 19133), and the proxy connects
to the actual server (port 19132), forwarding all packets bidirectionally.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for development.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pymc.conn import Connection
from pymc.dial import Dialer
from pymc.listener import ListenConfig, listen
from pymc.network import TCPNetwork
from pymc.proto.login.data import IdentityData
from pymc.proto.pool import Packet, UnknownPacket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("proxy")


async def forward_packets(
    src: Connection,
    dst: Connection,
    direction: str,
) -> None:
    """Forward packets from src to dst, logging each one."""
    try:
        while not src.closed and not dst.closed:
            pk = await src.read_packet()
            name = type(pk).__name__
            if isinstance(pk, UnknownPacket):
                name = f"Unknown(0x{pk.packet_id:02x})"
            logger.info("[%s] %s", direction, name)
            await dst.write_packet(pk)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.info("[%s] connection closed: %s", direction, e)


async def handle_connection(
    client_conn: Connection,
    remote_address: str,
    network: TCPNetwork,
) -> None:
    """Handle a single proxied connection."""
    logger.info("New client connected, dialing remote %s", remote_address)

    dialer = Dialer(
        identity_data=IdentityData(
            display_name="ProxyPlayer",
            identity="00000000-0000-0000-0000-000000000000",
        ),
        network=network,
    )

    try:
        server_conn = await dialer.dial(remote_address)
    except Exception as e:
        logger.error("Failed to connect to remote: %s", e)
        await client_conn.close()
        return

    logger.info("Connected to remote server")

    # Forward packets bidirectionally.
    client_to_server = asyncio.create_task(
        forward_packets(client_conn, server_conn, "C→S")
    )
    server_to_client = asyncio.create_task(
        forward_packets(server_conn, client_conn, "S→C")
    )

    # Wait for either direction to finish.
    done, pending = await asyncio.wait(
        [client_to_server, server_to_client],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Clean up.
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    await server_conn.close()
    await client_conn.close()
    logger.info("Connection closed")


async def run_proxy(listen_addr: str, remote_addr: str) -> None:
    """Run the MITM proxy."""
    network = TCPNetwork()
    config = ListenConfig(
        server_name="pymc Proxy",
        authentication_disabled=True,
    )

    logger.info("Starting proxy: %s → %s", listen_addr, remote_addr)
    server = await listen(listen_addr, config=config, network=network)

    try:
        while True:
            client_conn = await server.accept()
            asyncio.create_task(
                handle_connection(client_conn, remote_addr, network)
            )
    except asyncio.CancelledError:
        pass
    finally:
        await server.close()


def main():
    parser = argparse.ArgumentParser(description="Minecraft Bedrock MITM Proxy")
    parser.add_argument(
        "--listen", default="0.0.0.0:19133",
        help="Address to listen on (default: 0.0.0.0:19133)",
    )
    parser.add_argument(
        "--remote", default="127.0.0.1:19132",
        help="Remote server address (default: 127.0.0.1:19132)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_proxy(args.listen, args.remote))
    except KeyboardInterrupt:
        logger.info("Proxy stopped")


if __name__ == "__main__":
    main()
