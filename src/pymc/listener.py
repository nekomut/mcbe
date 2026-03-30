"""Server listener for Minecraft Bedrock Edition connections.

Mirrors gophertunnel/minecraft/listener.go.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os

import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import ec

from pymc.conn import Connection
from pymc.network import Network, NetworkListener, TCPNetwork
from pymc.proto.encryption import compute_shared_secret, derive_key
from pymc.proto.login.data import ClientData, IdentityData
from pymc.proto.login.request import marshal_public_key, parse_request
from pymc.proto.packet.chunk_radius_updated import ChunkRadiusUpdated
from pymc.proto.packet.disconnect import Disconnect
from pymc.proto.packet.handshake import ClientToServerHandshake, ServerToClientHandshake
from pymc.proto.packet.login import Login
from pymc.proto.packet.network_settings import NetworkSettings
from pymc.proto.packet.play_status import PlayStatus, STATUS_LOGIN_SUCCESS, STATUS_PLAYER_SPAWN
from pymc.proto.packet.request_chunk_radius import RequestChunkRadius
from pymc.proto.packet.request_network_settings import RequestNetworkSettings
from pymc.proto.packet.resource_packs import (
    PACK_RESPONSE_ALL_PACKS_DOWNLOADED,
    PACK_RESPONSE_COMPLETED,
    ResourcePackClientResponse,
    ResourcePackStack,
    ResourcePacksInfo,
)
from pymc.proto.packet.set_local_player_as_initialised import SetLocalPlayerAsInitialised
from pymc.proto.pool import COMPRESSION_FLATE, Packet, client_pool

logger = logging.getLogger(__name__)

# Current protocol version.
PROTOCOL_VERSION = 729


class ListenConfig:
    """Configuration for a Listener."""

    def __init__(
        self,
        *,
        max_players: int = 20,
        authentication_disabled: bool = True,
        compression: int = COMPRESSION_FLATE,
        compression_threshold: int = 256,
        flush_rate: float = 0.05,
        server_name: str = "pymc Server",
        game_version: str = "1.21.50",
    ) -> None:
        self.max_players = max_players
        self.authentication_disabled = authentication_disabled
        self.compression = compression
        self.compression_threshold = compression_threshold
        self.flush_rate = flush_rate
        self.server_name = server_name
        self.game_version = game_version


class Listener:
    """Accepts incoming Minecraft Bedrock Edition connections.

    Usage:
        listener = await listen("0.0.0.0:19132")
        conn = await listener.accept()
    """

    def __init__(
        self,
        network_listener: NetworkListener,
        config: ListenConfig,
        private_key: ec.EllipticCurvePrivateKey,
    ) -> None:
        self._listener = network_listener
        self._config = config
        self._private_key = private_key
        self._incoming: asyncio.Queue[Connection] = asyncio.Queue()
        self._closed = False
        self._accept_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start accepting connections in the background."""
        self._accept_task = asyncio.create_task(self._accept_loop())

    async def accept(self) -> Connection:
        """Wait for and return the next fully-authenticated connection."""
        return await self._incoming.get()

    async def close(self) -> None:
        """Stop accepting connections."""
        if self._closed:
            return
        self._closed = True
        if self._accept_task:
            self._accept_task.cancel()
            try:
                await self._accept_task
            except asyncio.CancelledError:
                pass
        await self._listener.close()

    async def _accept_loop(self) -> None:
        """Accept raw connections and run handshake in background tasks."""
        try:
            while not self._closed:
                try:
                    transport = await self._listener.accept()
                except Exception:
                    if not self._closed:
                        logger.error("accept error", exc_info=True)
                    break
                asyncio.create_task(self._handle_connection(transport))
        except asyncio.CancelledError:
            pass

    async def _handle_connection(self, transport) -> None:
        """Handle a single incoming connection through the handshake."""
        pool = client_pool()
        conn = Connection(transport, pool, flush_rate=self._config.flush_rate)
        await conn.start()

        try:
            await self._server_handshake(conn)
            await self._incoming.put(conn)
        except Exception as e:
            logger.warning("handshake failed: %s", e)
            try:
                await conn.write_packet(Disconnect(
                    reason=0,
                    hide_disconnection_screen=False,
                    message=f"Login failed: {e}",
                    filtered_message="",
                ))
                await conn.flush()
            except Exception:
                pass
            await conn.close()

    async def _server_handshake(self, conn: Connection) -> None:
        """Perform the server-side login handshake."""
        # 1. Wait for RequestNetworkSettings.
        pk = await self._expect(conn, RequestNetworkSettings, timeout=10.0)
        protocol = pk.client_protocol
        if protocol != PROTOCOL_VERSION:
            logger.warning("client protocol %d != expected %d", protocol, PROTOCOL_VERSION)

        # 2. Send NetworkSettings.
        await conn.write_packet_immediate(NetworkSettings(
            compression_threshold=self._config.compression_threshold,
            compression_algorithm=self._config.compression,
            client_throttle=False,
            client_throttle_threshold=0,
            client_throttle_scalar=0.0,
        ))

        # Enable compression for subsequent packets.
        conn.enable_compression(
            self._config.compression, self._config.compression_threshold
        )

        # 3. Wait for Login.
        login_pk = await self._expect(conn, Login, timeout=10.0)
        identity, client_data, auth_result = parse_request(login_pk.connection_request)
        logger.info("player login: %s (XUID: %s)", identity.display_name, identity.xuid)

        # 4. Enable encryption.
        if auth_result.public_key is not None:
            await self._enable_encryption(conn, auth_result.public_key)

            # 5. Wait for ClientToServerHandshake.
            await self._expect(conn, ClientToServerHandshake, timeout=10.0)

        # 6. Send PlayStatus (login success).
        await conn.write_packet(PlayStatus(status=STATUS_LOGIN_SUCCESS))

        # 7. Send ResourcePacksInfo.
        await conn.write_packet(ResourcePacksInfo(
            texture_pack_required=False,
        ))
        await conn.flush()

        # 8. Wait for ResourcePackClientResponse.
        resp = await self._expect(conn, ResourcePackClientResponse, timeout=10.0)

        # 9. Send ResourcePackStack.
        await conn.write_packet(ResourcePackStack(
            texture_pack_required=False,
            base_game_version=self._config.game_version,
        ))
        await conn.flush()

        # 10. Wait for ResourcePackClientResponse (completed).
        resp = await self._expect(conn, ResourcePackClientResponse, timeout=10.0)

        # Note: StartGame and other game state packets would be sent here.
        # For now, we consider the handshake complete at this point.

    async def _enable_encryption(
        self, conn: Connection, client_public_key: ec.EllipticCurvePublicKey
    ) -> None:
        """Generate salt, compute shared secret, and enable encryption."""
        salt = os.urandom(16)

        # Create JWT with salt and server's public key.
        pub_key_b64 = marshal_public_key(self._private_key.public_key())
        salt_b64 = base64.b64encode(salt).decode().rstrip("=")

        token = pyjwt.encode(
            {"salt": salt_b64},
            self._private_key,
            algorithm="ES384",
            headers={"x5u": pub_key_b64},
        )

        # Send ServerToClientHandshake.
        await conn.write_packet(ServerToClientHandshake(jwt=token.encode()))
        await conn.flush()

        # Compute shared secret and derive key.
        shared_secret = compute_shared_secret(self._private_key, client_public_key)
        key = derive_key(salt, shared_secret)

        conn.enable_encryption(key)

    @staticmethod
    async def _expect(
        conn: Connection,
        packet_type: type[Packet],
        timeout: float = 10.0,
    ) -> Packet:
        """Read packets until we get the expected type."""
        while True:
            pk = await asyncio.wait_for(conn.read_packet(), timeout=timeout)
            if isinstance(pk, packet_type):
                return pk
            logger.debug("server skipping unexpected packet: %s", type(pk).__name__)


async def listen(
    address: str,
    config: ListenConfig | None = None,
    network: Network | None = None,
) -> Listener:
    """Start listening for Minecraft Bedrock Edition connections.

    Args:
        address: Address to listen on (e.g., "0.0.0.0:19132").
        config: Server configuration.
        network: Network transport (defaults to TCP for testing).

    Returns:
        A started Listener ready to accept connections.
    """
    cfg = config or ListenConfig()
    net = network or TCPNetwork()

    private_key = ec.generate_private_key(ec.SECP384R1())
    network_listener = await net.listen(address)

    listener = Listener(network_listener, cfg, private_key)
    await listener.start()
    return listener
