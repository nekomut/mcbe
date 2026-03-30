"""Integration tests for Dialer and Listener handshake flow."""

import asyncio

import pytest

from pymc.conn import Connection
from pymc.dial import Dialer
from pymc.listener import Listener, ListenConfig, listen
from pymc.network import TCPNetwork
from pymc.proto.login.data import IdentityData, ClientData
from pymc.proto.packet.play_status import PlayStatus


async def _find_free_port() -> int:
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()
    return port


@pytest.mark.asyncio(loop_scope="function")
async def test_dialer_listener_handshake():
    """Test complete client-server handshake using Dialer + Listener."""
    port = await _find_free_port()
    address = f"127.0.0.1:{port}"
    network = TCPNetwork()

    # Start server.
    config = ListenConfig(
        server_name="test-server",
        authentication_disabled=True,
    )
    server = await listen(address, config=config, network=network)

    try:
        # Client connects.
        dialer = Dialer(
            identity_data=IdentityData(
                display_name="TestPlayer",
                identity="00000000-0000-0000-0000-000000000001",
            ),
            client_data=ClientData(
                game_version="1.21.50",
                device_os=7,
            ),
            network=network,
        )

        # Run dialer and accept concurrently.
        # Note: The full handshake requires StartGame + PlayStatus(PLAYER_SPAWN)
        # from the server side. For this test, we manually handle the server side
        # after accept() to complete the spawn flow.

        async def server_side():
            conn = await asyncio.wait_for(server.accept(), timeout=10.0)
            # After handshake, server would send StartGame, etc.
            # Send PlayStatus(PLAYER_SPAWN) to complete the dialer's spawn wait.
            await conn.write_packet(PlayStatus(status=3))  # STATUS_PLAYER_SPAWN
            await conn.flush()
            return conn

        async def client_side():
            return await asyncio.wait_for(
                dialer.dial(address), timeout=15.0
            )

        server_conn, client_conn = await asyncio.gather(
            server_side(), client_side()
        )

        # Both connections should be active.
        assert not server_conn.closed
        assert not client_conn.closed

        await server_conn.close()
        await client_conn.close()

    finally:
        await server.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_encrypted_packet_exchange():
    """Test that packets can be exchanged after encrypted handshake."""
    port = await _find_free_port()
    address = f"127.0.0.1:{port}"
    network = TCPNetwork()

    config = ListenConfig(authentication_disabled=True)
    server = await listen(address, config=config, network=network)

    try:
        dialer = Dialer(
            identity_data=IdentityData(
                display_name="EncPlayer",
                identity="00000000-0000-0000-0000-000000000002",
            ),
            network=network,
        )

        async def server_side():
            conn = await asyncio.wait_for(server.accept(), timeout=10.0)
            await conn.write_packet(PlayStatus(status=3))
            await conn.flush()
            return conn

        server_conn, client_conn = await asyncio.gather(
            server_side(),
            asyncio.wait_for(dialer.dial(address), timeout=15.0),
        )

        # Exchange packets over the encrypted connection.
        from pymc.proto.packet.set_local_player_as_initialised import (
            SetLocalPlayerAsInitialised,
        )

        await client_conn.write_packet(
            SetLocalPlayerAsInitialised(entity_runtime_id=42)
        )
        await client_conn.flush()

        pk = await asyncio.wait_for(server_conn.read_packet(), timeout=5.0)
        assert isinstance(pk, SetLocalPlayerAsInitialised)
        assert pk.entity_runtime_id == 42

        await server_conn.close()
        await client_conn.close()

    finally:
        await server.close()
