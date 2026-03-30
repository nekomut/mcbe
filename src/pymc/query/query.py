"""UT3 query protocol for Minecraft Bedrock Edition servers.

Mirrors gophertunnel/minecraft/query/query.go.
Uses UDP to query server information via the UT3 query protocol.
"""

from __future__ import annotations

import asyncio
import random
import struct

# Query type constants.
_QUERY_TYPE_HANDSHAKE = 9
_QUERY_TYPE_INFORMATION = 0


async def query(address: str, timeout: float = 5.0) -> dict[str, str]:
    """Query a Minecraft Bedrock server for information.

    Args:
        address: Server address in "host:port" format.
        timeout: Timeout in seconds.

    Returns:
        Dict of server information (e.g., hostname, gametype, map, etc.).
    """
    host, port_str = address.rsplit(":", 1)
    port = int(port_str)

    loop = asyncio.get_running_loop()
    transport, protocol = await asyncio.wait_for(
        loop.create_datagram_endpoint(
            lambda: _QueryProtocol(),
            remote_addr=(host, port),
        ),
        timeout=timeout,
    )

    try:
        proto: _QueryProtocol = protocol

        # Step 1: Handshake.
        seq = random.randint(0, 0xFFFFFFFF)
        handshake_req = _encode_request(_QUERY_TYPE_HANDSHAKE, seq)
        transport.sendto(handshake_req)

        response_data = await asyncio.wait_for(proto.receive(), timeout=timeout)
        response_num = _parse_handshake_response(response_data)

        # Step 2: Information request.
        info_req = _encode_request(_QUERY_TYPE_INFORMATION, seq, response_num)
        transport.sendto(info_req)

        response_data = await asyncio.wait_for(proto.receive(), timeout=timeout)
        return _parse_info_response(response_data)

    finally:
        transport.close()


class _QueryProtocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        self._queue.put_nowait(data)

    async def receive(self) -> bytes:
        return await self._queue.get()


def _encode_request(
    query_type: int, sequence: int, response_num: int | None = None
) -> bytes:
    """Encode a UT3 query request packet."""
    buf = bytearray()
    buf.extend(b"\xfe\xfd")  # Magic
    buf.append(query_type)
    buf.extend(struct.pack(">I", sequence))
    if response_num is not None:
        buf.extend(struct.pack(">i", response_num))
        buf.extend(b"\x00\x00\x00\x00")  # Padding
    return bytes(buf)


def _parse_handshake_response(data: bytes) -> int:
    """Parse handshake response to get the response number."""
    # Skip type (1 byte) + sequence (4 bytes).
    payload = data[5:]
    # Response number is a null-terminated string of digits.
    num_str = payload.split(b"\x00")[0].decode()
    return int(num_str)


def _parse_info_response(data: bytes) -> dict[str, str]:
    """Parse information response into key-value pairs."""
    # Skip type (1 byte) + sequence (4 bytes) + padding (11 bytes).
    payload = data[16:]

    result: dict[str, str] = {}
    parts = payload.split(b"\x00")

    i = 0
    while i < len(parts) - 1:
        key = parts[i].decode(errors="replace")
        if not key:
            i += 1
            continue
        value = parts[i + 1].decode(errors="replace") if i + 1 < len(parts) else ""
        result[key] = value
        i += 2

    return result
