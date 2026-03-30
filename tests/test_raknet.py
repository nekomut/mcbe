"""Tests for the RakNet protocol module."""

from __future__ import annotations

import asyncio
import struct

import pytest

from pymc.raknet.protocol import (
    ACK,
    FRAME_SET_MIN,
    NACK,
    OPEN_CONNECTION_REPLY_1,
    OPEN_CONNECTION_REPLY_2,
    OPEN_CONNECTION_REQUEST_1,
    OPEN_CONNECTION_REQUEST_2,
    RAKNET_MAGIC,
    RAKNET_PROTOCOL_VERSION,
    RELIABLE_ORDERED,
    RELIABLE_TYPES,
    ORDERED_TYPES,
    SEQUENCED_TYPES,
    Frame,
    decode_ack_nack,
    decode_frame_set,
    encode_ack,
    encode_frame_set,
    encode_nack,
    read_address,
    read_uint24le,
    write_address,
    write_uint24le,
)
from pymc.raknet.connection import (
    RakNetClientConnection,
    RakNetClientProtocol,
    RakNetServerConnection,
    _FragmentBuffer,
)


# ── Binary helpers ──────────────────────────────────────────────


class TestUint24LE:
    def test_roundtrip_zero(self):
        data = write_uint24le(0)
        assert len(data) == 3
        val, offset = read_uint24le(data)
        assert val == 0
        assert offset == 3

    def test_roundtrip_values(self):
        for v in [1, 255, 256, 65535, 0xFFFFFF]:
            data = write_uint24le(v)
            val, _ = read_uint24le(data)
            assert val == v, f"Failed for {v}"

    def test_read_with_offset(self):
        buf = b"\xAA" + write_uint24le(42)
        val, offset = read_uint24le(buf, 1)
        assert val == 42
        assert offset == 4


class TestAddress:
    def test_ipv4_roundtrip(self):
        data = write_address("127.0.0.1", 19132)
        host, port, offset = read_address(data)
        assert host == "127.0.0.1"
        assert port == 19132
        assert offset == 7  # version(1) + parts(4) + port(2)

    def test_ipv4_various(self):
        for addr in [("192.168.1.1", 25565), ("0.0.0.0", 0), ("255.255.255.255", 65535)]:
            data = write_address(*addr)
            host, port, _ = read_address(data)
            assert host == addr[0]
            assert port == addr[1]


# ── Frame ───────────────────────────────────────────────────────


class TestFrame:
    def test_simple_roundtrip(self):
        frame = Frame(
            reliability=RELIABLE_ORDERED,
            body=b"Hello, RakNet!",
            reliable_index=5,
            ordered_index=3,
            order_channel=0,
        )
        encoded = frame.encode()
        decoded, offset = Frame.decode(encoded)
        assert decoded.reliability == RELIABLE_ORDERED
        assert decoded.body == b"Hello, RakNet!"
        assert decoded.reliable_index == 5
        assert decoded.ordered_index == 3
        assert decoded.order_channel == 0
        assert not decoded.fragmented

    def test_fragmented_roundtrip(self):
        frame = Frame(
            reliability=RELIABLE_ORDERED,
            body=b"fragment data",
            reliable_index=10,
            ordered_index=7,
            order_channel=0,
            fragmented=True,
            compound_size=3,
            compound_id=42,
            fragment_index=1,
        )
        encoded = frame.encode()
        decoded, _ = Frame.decode(encoded)
        assert decoded.fragmented
        assert decoded.compound_size == 3
        assert decoded.compound_id == 42
        assert decoded.fragment_index == 1
        assert decoded.body == b"fragment data"

    def test_unreliable_frame(self):
        frame = Frame(reliability=0, body=b"unreliable")
        encoded = frame.encode()
        decoded, _ = Frame.decode(encoded)
        assert decoded.reliability == 0
        assert decoded.body == b"unreliable"


# ── Frame Set ───────────────────────────────────────────────────


class TestFrameSet:
    def test_roundtrip_single_frame(self):
        frames = [Frame(reliability=RELIABLE_ORDERED, body=b"test", reliable_index=0, ordered_index=0)]
        data = encode_frame_set(42, frames)
        assert data[0] == FRAME_SET_MIN
        seq_num, decoded_frames = decode_frame_set(data)
        assert seq_num == 42
        assert len(decoded_frames) == 1
        assert decoded_frames[0].body == b"test"

    def test_roundtrip_multiple_frames(self):
        frames = [
            Frame(reliability=RELIABLE_ORDERED, body=b"frame1", reliable_index=0, ordered_index=0),
            Frame(reliability=RELIABLE_ORDERED, body=b"frame2", reliable_index=1, ordered_index=1),
        ]
        data = encode_frame_set(100, frames)
        seq_num, decoded_frames = decode_frame_set(data)
        assert seq_num == 100
        assert len(decoded_frames) == 2
        assert decoded_frames[0].body == b"frame1"
        assert decoded_frames[1].body == b"frame2"


# ── ACK / NACK ──────────────────────────────────────────────────


class TestAckNack:
    def test_ack_single(self):
        data = encode_ack([5])
        numbers = decode_ack_nack(data)
        assert numbers == [5]
        assert data[0] == ACK

    def test_nack_single(self):
        data = encode_nack([10])
        numbers = decode_ack_nack(data)
        assert numbers == [10]
        assert data[0] == NACK

    def test_ack_range(self):
        data = encode_ack([1, 2, 3, 4, 5])
        numbers = decode_ack_nack(data)
        assert numbers == [1, 2, 3, 4, 5]

    def test_ack_multiple_ranges(self):
        data = encode_ack([1, 2, 3, 10, 11, 20])
        numbers = decode_ack_nack(data)
        assert sorted(numbers) == [1, 2, 3, 10, 11, 20]

    def test_ack_empty(self):
        data = encode_ack([])
        numbers = decode_ack_nack(data)
        assert numbers == []

    def test_ack_dedup(self):
        data = encode_ack([5, 5, 5])
        numbers = decode_ack_nack(data)
        assert numbers == [5]


# ── Fragment Buffer ─────────────────────────────────────────────


class TestFragmentBuffer:
    def test_reassembly(self):
        buf = _FragmentBuffer(compound_size=3)
        assert buf.add(0, b"AAA") is None
        assert buf.add(2, b"CCC") is None
        result = buf.add(1, b"BBB")
        assert result == b"AAABBBCCC"

    def test_single_fragment(self):
        buf = _FragmentBuffer(compound_size=1)
        result = buf.add(0, b"only")
        assert result == b"only"


# ── Reliability type sets ───────────────────────────────────────


class TestReliabilityTypes:
    def test_reliable_types(self):
        assert 2 in RELIABLE_TYPES
        assert 3 in RELIABLE_TYPES
        assert 0 not in RELIABLE_TYPES

    def test_ordered_types(self):
        assert 3 in ORDERED_TYPES
        assert 1 in ORDERED_TYPES
        assert 0 not in ORDERED_TYPES

    def test_sequenced_types(self):
        assert 1 in SEQUENCED_TYPES
        assert 4 in SEQUENCED_TYPES
        assert 3 not in SEQUENCED_TYPES


# ── RakNet Connection Integration ───────────────────────────────


@pytest.mark.asyncio
async def test_client_server_game_packet():
    """Test RakNet client-server game packet exchange via loopback UDP."""
    loop = asyncio.get_running_loop()

    # Create server
    server_guid = 12345
    from pymc.raknet.network import RakNetListener
    listener = RakNetListener(server_guid=server_guid)

    server_transport, _ = await loop.create_datagram_endpoint(
        lambda: listener._protocol,
        local_addr=("127.0.0.1", 0),
    )
    listener._transport = server_transport
    listener.start()

    server_addr = server_transport.get_extra_info("sockname")

    # Create client protocol
    client_proto = RakNetClientProtocol()
    client_transport, _ = await loop.create_datagram_endpoint(
        lambda: client_proto,
        local_addr=("127.0.0.1", 0),
    )
    client_addr = client_transport.get_extra_info("sockname")

    try:
        # Simulate offline handshake manually for testing
        mtu = 1400

        # OpenConnectionRequest1
        req1 = struct.pack("B", OPEN_CONNECTION_REQUEST_1)
        req1 += RAKNET_MAGIC
        req1 += struct.pack("B", RAKNET_PROTOCOL_VERSION)
        req1 += b"\x00" * (mtu - len(req1) - 28)
        client_proto.send(req1, server_addr)
        await asyncio.sleep(0.05)

        # Get Reply1
        data, addr = await client_proto.recv(timeout=2.0)
        assert data[0] == OPEN_CONNECTION_REPLY_1

        # OpenConnectionRequest2
        req2 = struct.pack("B", OPEN_CONNECTION_REQUEST_2)
        req2 += RAKNET_MAGIC
        req2 += write_address(server_addr[0], server_addr[1])
        req2 += struct.pack(">H", mtu)
        req2 += struct.pack(">q", 99999)
        client_proto.send(req2, server_addr)
        await asyncio.sleep(0.05)

        # Get Reply2
        data, addr = await client_proto.recv(timeout=2.0)
        assert data[0] == OPEN_CONNECTION_REPLY_2

        # Server should have a connection now
        server_conn = await asyncio.wait_for(listener.accept(), timeout=2.0)
        assert isinstance(server_conn, RakNetServerConnection)

        # Create client connection
        client_conn = RakNetClientConnection(
            protocol=client_proto,
            remote_addr=server_addr,
            local_addr=client_addr,
            mtu=mtu,
            client_guid=99999,
            server_guid=server_guid,
        )
        client_conn.start()

        # Client sends game packet
        test_data = b"\xfe\x00\x01\x02\x03Hello World"
        await client_conn.write_packet(test_data)
        await asyncio.sleep(0.1)

        # Server reads game packet
        received = await asyncio.wait_for(server_conn.read_packet(), timeout=2.0)
        assert received == test_data

        # Server sends game packet back
        reply_data = b"\xfe\x00\x04\x05Reply"
        await server_conn.write_packet(reply_data)
        await asyncio.sleep(0.1)

        # Client reads game packet
        received = await asyncio.wait_for(client_conn.read_packet(), timeout=2.0)
        assert received == reply_data

    finally:
        if "client_conn" in dir():
            await client_conn.close()
        await listener.close()
        client_transport.close()


@pytest.mark.asyncio
async def test_ping_pong():
    """Test RakNet UnconnectedPing/Pong."""
    loop = asyncio.get_running_loop()

    from pymc.raknet.network import RakNetListener
    listener = RakNetListener(server_guid=54321)

    server_transport, _ = await loop.create_datagram_endpoint(
        lambda: listener._protocol,
        local_addr=("127.0.0.1", 0),
    )
    listener._transport = server_transport
    listener.set_pong_data(b"MCPE;TestServer;100;1.21.0;0;10;54321;pymc;Survival;1;19132;19132;0;")

    server_addr = server_transport.get_extra_info("sockname")

    try:
        from pymc.raknet.network import RakNetNetwork
        network = RakNetNetwork(client_guid=11111)
        pong = await network.ping(f"{server_addr[0]}:{server_addr[1]}")
        assert b"MCPE" in pong
        assert b"TestServer" in pong
    finally:
        server_transport.close()
