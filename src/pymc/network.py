"""Network abstraction layer for Minecraft Bedrock Edition.

Mirrors gophertunnel/minecraft/network.go and raknet.go.
Provides a pluggable transport layer (RakNet or other).
"""

from __future__ import annotations

import asyncio
import logging
import struct
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NetworkConnection(ABC):
    """Abstract connection from a Network transport."""

    @abstractmethod
    async def read_packet(self) -> bytes:
        """Read a single packet. Blocks until data is available."""
        ...

    @abstractmethod
    async def write_packet(self, data: bytes) -> None:
        """Write a single packet."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close this connection."""
        ...


class NetworkListener(ABC):
    """Abstract listener that accepts incoming connections."""

    @abstractmethod
    async def accept(self) -> NetworkConnection:
        """Accept a new incoming connection."""
        ...

    @abstractmethod
    def set_pong_data(self, data: bytes) -> None:
        """Set server status (pong) response data."""
        ...

    @abstractmethod
    def server_id(self) -> int:
        """Return the unique server ID for this session."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Stop listening and close."""
        ...


class Network(ABC):
    """Abstract network transport (RakNet, TCP, etc.)."""

    @abstractmethod
    async def connect(self, address: str) -> NetworkConnection:
        """Connect to a server at the given address (host:port)."""
        ...

    @abstractmethod
    async def ping(self, address: str) -> bytes:
        """Ping a server and return the pong data."""
        ...

    @abstractmethod
    async def listen(self, address: str) -> NetworkListener:
        """Start listening for connections on the given address."""
        ...


# ── TCP-based transport for testing ──────────────────────────────


class TCPConnection(NetworkConnection):
    """TCP-based connection using length-prefixed packets.

    Useful for testing without RakNet dependency.
    Each packet is prefixed with a 4-byte big-endian length.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    async def read_packet(self) -> bytes:
        length_bytes = await self._reader.readexactly(4)
        length = struct.unpack(">I", length_bytes)[0]
        return await self._reader.readexactly(length)

    async def write_packet(self, data: bytes) -> None:
        self._writer.write(struct.pack(">I", len(data)))
        self._writer.write(data)
        await self._writer.drain()

    async def close(self) -> None:
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except Exception:
            pass


class TCPListener(NetworkListener):
    """TCP listener for testing."""

    def __init__(self, server: asyncio.Server) -> None:
        self._server = server
        self._queue: asyncio.Queue[TCPConnection] = asyncio.Queue()
        self._id = id(self)

    async def accept(self) -> NetworkConnection:
        return await self._queue.get()

    def set_pong_data(self, data: bytes) -> None:
        pass  # Not applicable for TCP

    def server_id(self) -> int:
        return self._id

    async def close(self) -> None:
        self._server.close()
        await self._server.wait_closed()


class TCPNetwork(Network):
    """TCP network transport for testing without RakNet."""

    async def connect(self, address: str) -> NetworkConnection:
        host, port_str = address.rsplit(":", 1)
        port = int(port_str)
        reader, writer = await asyncio.open_connection(host, port)
        return TCPConnection(reader, writer)

    async def ping(self, address: str) -> bytes:
        raise NotImplementedError("TCP transport does not support ping")

    async def listen(self, address: str) -> NetworkListener:
        host, port_str = address.rsplit(":", 1)
        port = int(port_str)
        listener = TCPListener.__new__(TCPListener)
        listener._queue = asyncio.Queue()
        listener._id = id(listener)

        async def on_connect(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            conn = TCPConnection(reader, writer)
            await listener._queue.put(conn)

        server = await asyncio.start_server(on_connect, host, port)
        listener._server = server
        return listener


def format_pong_data(
    server_name: str,
    protocol_version: int,
    game_version: str,
    player_count: int,
    max_players: int,
    server_id: int,
    sub_name: str = "pymc",
    game_mode: str = "Survival",
    port: int = 19132,
) -> bytes:
    """Format server status pong data for Minecraft Bedrock Edition."""
    return (
        f"MCPE;{server_name};{protocol_version};{game_version};"
        f"{player_count};{max_players};{server_id};{sub_name};"
        f"{game_mode};1;{port};{port};0;"
    ).encode()
