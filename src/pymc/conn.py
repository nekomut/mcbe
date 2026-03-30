"""Connection for Minecraft Bedrock Edition protocol.

Mirrors gophertunnel/minecraft/conn.go. Handles packet read/write with
buffering, compression, and encryption over an abstract transport.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol as TypingProtocol

from pymc.proto.encryption import PacketDecrypt, PacketEncrypt
from pymc.proto.pool import (
    BATCH_HEADER,
    COMPRESSION_FLATE,
    Packet,
    PacketPool,
    UnknownPacket,
    decode_batch,
    decode_packet,
    encode_batch,
    encode_packet,
)

logger = logging.getLogger(__name__)

# Default flush interval in seconds (matches Go's 50ms).
DEFAULT_FLUSH_RATE = 0.05


class Transport(TypingProtocol):
    """Abstract transport interface for sending/receiving raw packets.

    Implementations wrap RakNet or other reliable transports.
    """

    async def read_packet(self) -> bytes:
        """Read a single raw packet from the transport."""
        ...

    async def write_packet(self, data: bytes) -> None:
        """Write a single raw packet to the transport."""
        ...

    async def close(self) -> None:
        """Close the transport."""
        ...


class Connection:
    """Manages packet-level communication with a Minecraft Bedrock server/client.

    Features:
    - Automatic 50ms packet batching and flushing
    - Compression (flate/snappy)
    - Encryption (AES-256-CTR with SHA-256 checksums)
    - Async context manager support
    """

    def __init__(
        self,
        transport: Transport,
        pool: PacketPool,
        *,
        flush_rate: float = DEFAULT_FLUSH_RATE,
    ) -> None:
        self._transport = transport
        self._pool = pool
        self._flush_rate = flush_rate

        # Compression settings.
        self._compression: int | None = None
        self._compression_threshold: int = 256

        # Encryption.
        self._encrypt: PacketEncrypt | None = None
        self._decrypt: PacketDecrypt | None = None

        # Packet buffering.
        self._send_buffer: list[bytes] = []
        self._send_lock = asyncio.Lock()

        # Received packet queue.
        self._recv_queue: asyncio.Queue[Packet] = asyncio.Queue(maxsize=128)

        # Lifecycle.
        self._closed = False
        self._close_event = asyncio.Event()
        self._flush_task: asyncio.Task[None] | None = None
        self._read_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start background tasks for flushing and reading."""
        if self._flush_rate > 0:
            self._flush_task = asyncio.create_task(self._flush_loop())
        self._read_task = asyncio.create_task(self._read_loop())

    async def __aenter__(self) -> Connection:
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ── Compression ──────────────────────────────────────────────

    def enable_compression(
        self, algorithm: int = COMPRESSION_FLATE, threshold: int = 256
    ) -> None:
        """Enable packet compression."""
        self._compression = algorithm
        self._compression_threshold = threshold

    # ── Encryption ───────────────────────────────────────────────

    def enable_encryption(self, key: bytes) -> None:
        """Enable AES-256-CTR encryption with the given 32-byte key."""
        self._encrypt = PacketEncrypt(key)
        self._decrypt = PacketDecrypt(key)

    # ── Writing ──────────────────────────────────────────────────

    async def write_packet(self, pk: Packet) -> None:
        """Buffer a packet for sending. It will be flushed automatically."""
        data = encode_packet(pk)
        async with self._send_lock:
            self._send_buffer.append(data)

    async def flush(self) -> None:
        """Flush all buffered packets as a single batch."""
        async with self._send_lock:
            if not self._send_buffer:
                return
            to_send = self._send_buffer
            self._send_buffer = []

        batch = bytearray(
            encode_batch(
                to_send,
                compression=self._compression,
                compression_threshold=self._compression_threshold,
            )
        )

        if self._encrypt is not None:
            batch = self._encrypt.encrypt(batch)

        await self._transport.write_packet(bytes(batch))

    async def write_packet_immediate(self, pk: Packet) -> None:
        """Write a single packet immediately without buffering."""
        data = encode_packet(pk)
        batch = bytearray(
            encode_batch(
                [data],
                compression=self._compression,
                compression_threshold=self._compression_threshold,
            )
        )
        if self._encrypt is not None:
            batch = self._encrypt.encrypt(batch)
        await self._transport.write_packet(bytes(batch))

    # ── Reading ──────────────────────────────────────────────────

    async def read_packet(self) -> Packet:
        """Read the next packet. Blocks until a packet is available."""
        return await self._recv_queue.get()

    def read_packet_nowait(self) -> Packet | None:
        """Read the next packet if available, else return None."""
        try:
            return self._recv_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    # ── Lifecycle ────────────────────────────────────────────────

    async def close(self) -> None:
        """Flush remaining packets and close the connection."""
        if self._closed:
            return
        self._closed = True
        self._close_event.set()

        # Flush remaining packets.
        try:
            await self.flush()
        except Exception:
            pass

        # Cancel background tasks.
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        if self._read_task is not None:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        await self._transport.close()

    @property
    def closed(self) -> bool:
        return self._closed

    # ── Internal ─────────────────────────────────────────────────

    async def _flush_loop(self) -> None:
        """Periodically flush buffered packets."""
        try:
            while not self._closed:
                await asyncio.sleep(self._flush_rate)
                try:
                    await self.flush()
                except Exception as e:
                    if not self._closed:
                        logger.error("flush error: %s", e)
                        break
        except asyncio.CancelledError:
            pass

    async def _read_loop(self) -> None:
        """Continuously read and decode packets from the transport."""
        try:
            while not self._closed:
                try:
                    raw = await self._transport.read_packet()
                except Exception as e:
                    if not self._closed:
                        logger.error("transport read error: %s", e)
                    break

                try:
                    packets = self._decode_raw_batch(raw)
                except Exception as e:
                    logger.warning("decode error: %s", e)
                    continue

                for pk in packets:
                    await self._recv_queue.put(pk)

        except asyncio.CancelledError:
            pass

    def _decode_raw_batch(self, raw: bytes) -> list[Packet]:
        """Decode a raw batch (decrypt if needed, decompress, parse packets)."""
        data = bytearray(raw)

        if self._decrypt is not None:
            if len(data) < 2:
                raise ValueError("encrypted packet too short")
            # Header byte (0xFE) is not encrypted; decrypt bytes[1:]
            plaintext = self._decrypt.decrypt_and_verify(bytes(data[1:]))
            data = bytearray([data[0]]) + bytearray(plaintext)

        packet_list = decode_batch(
            bytes(data), compression=self._compression
        )

        results: list[Packet] = []
        for pkt_data in packet_list:
            pk = decode_packet(pkt_data, self._pool)
            results.append(pk)

        return results
