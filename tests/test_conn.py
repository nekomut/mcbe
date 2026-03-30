"""Tests for Connection class with TCP transport."""

import asyncio
import os

import pytest

from pymc.conn import Connection
from pymc.network import TCPNetwork
from pymc.proto.pool import (
    COMPRESSION_FLATE,
    server_pool,
)

# Import to populate pool.
from pymc.proto.packet.play_status import PlayStatus, STATUS_LOGIN_SUCCESS
from pymc.proto.packet.disconnect import Disconnect
from pymc.proto.packet.set_local_player_as_initialised import SetLocalPlayerAsInitialised


async def _create_pair() -> tuple[Connection, Connection, asyncio.Server]:
    """Create a connected pair of Connections using TCP loopback."""
    queue: asyncio.Queue = asyncio.Queue()

    async def on_connect(reader, writer):
        from pymc.network import TCPConnection
        await queue.put(TCPConnection(reader, writer))

    tcp_server = await asyncio.start_server(on_connect, "127.0.0.1", 0)
    port = tcp_server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    from pymc.network import TCPConnection
    client_transport = TCPConnection(reader, writer)
    server_transport = await asyncio.wait_for(queue.get(), timeout=2.0)

    pool = server_pool()
    server_conn = Connection(server_transport, pool, flush_rate=0.02)
    client_conn = Connection(client_transport, pool, flush_rate=0.02)

    await server_conn.start()
    await client_conn.start()

    return server_conn, client_conn, tcp_server


@pytest.mark.asyncio(loop_scope="function")
async def test_send_receive_packet():
    server, client, tcp = await _create_pair()
    try:
        await server.write_packet(PlayStatus(status=STATUS_LOGIN_SUCCESS))
        await server.flush()
        received = await asyncio.wait_for(client.read_packet(), timeout=2.0)
        assert isinstance(received, PlayStatus)
        assert received.status == STATUS_LOGIN_SUCCESS
    finally:
        await server.close()
        await client.close()
        tcp.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_multiple_packets_batched():
    server, client, tcp = await _create_pair()
    try:
        for i in range(5):
            await server.write_packet(SetLocalPlayerAsInitialised(entity_runtime_id=i))
        await server.flush()
        for i in range(5):
            pk = await asyncio.wait_for(client.read_packet(), timeout=2.0)
            assert isinstance(pk, SetLocalPlayerAsInitialised)
            assert pk.entity_runtime_id == i
    finally:
        await server.close()
        await client.close()
        tcp.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_auto_flush():
    server, client, tcp = await _create_pair()
    try:
        await server.write_packet(PlayStatus(status=STATUS_LOGIN_SUCCESS))
        received = await asyncio.wait_for(client.read_packet(), timeout=1.0)
        assert isinstance(received, PlayStatus)
    finally:
        await server.close()
        await client.close()
        tcp.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_with_compression():
    server, client, tcp = await _create_pair()
    try:
        server.enable_compression(COMPRESSION_FLATE, threshold=0)
        client.enable_compression(COMPRESSION_FLATE, threshold=0)

        await server.write_packet(Disconnect(
            reason=1, hide_disconnection_screen=False,
            message="Test compression", filtered_message="",
        ))
        await server.flush()
        received = await asyncio.wait_for(client.read_packet(), timeout=2.0)
        assert isinstance(received, Disconnect)
        assert received.message == "Test compression"
    finally:
        await server.close()
        await client.close()
        tcp.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_with_encryption():
    server, client, tcp = await _create_pair()
    try:
        key = os.urandom(32)
        server.enable_encryption(key)
        client.enable_encryption(key)

        await server.write_packet(PlayStatus(status=STATUS_LOGIN_SUCCESS))
        await server.flush()
        received = await asyncio.wait_for(client.read_packet(), timeout=2.0)
        assert isinstance(received, PlayStatus)
        assert received.status == STATUS_LOGIN_SUCCESS
    finally:
        await server.close()
        await client.close()
        tcp.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_compression_and_encryption():
    server, client, tcp = await _create_pair()
    try:
        key = os.urandom(32)
        server.enable_compression(COMPRESSION_FLATE, threshold=0)
        client.enable_compression(COMPRESSION_FLATE, threshold=0)
        server.enable_encryption(key)
        client.enable_encryption(key)

        for i in range(3):
            await server.write_packet(SetLocalPlayerAsInitialised(entity_runtime_id=i * 100))
        await server.flush()

        for i in range(3):
            pk = await asyncio.wait_for(client.read_packet(), timeout=2.0)
            assert isinstance(pk, SetLocalPlayerAsInitialised)
            assert pk.entity_runtime_id == i * 100
    finally:
        await server.close()
        await client.close()
        tcp.close()


@pytest.mark.asyncio(loop_scope="function")
async def test_context_manager():
    queue: asyncio.Queue = asyncio.Queue()

    async def on_connect(reader, writer):
        from pymc.network import TCPConnection
        await queue.put(TCPConnection(reader, writer))

    tcp_server = await asyncio.start_server(on_connect, "127.0.0.1", 0)
    port = tcp_server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    from pymc.network import TCPConnection
    transport = TCPConnection(reader, writer)
    await queue.get()  # Discard server side

    pool = server_pool()
    async with Connection(transport, pool, flush_rate=0.02) as conn:
        assert not conn.closed
    assert conn.closed
    tcp_server.close()
