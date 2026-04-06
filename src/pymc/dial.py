"""Client dialer for connecting to Minecraft Bedrock Edition servers.

Mirrors gophertunnel/minecraft/dial.go.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

from cryptography.hazmat.primitives.asymmetric import ec

from pymc.conn import Connection
from pymc.network import Network, TCPNetwork
from pymc.proto.encryption import compute_shared_secret, derive_key
from pymc.proto.login.data import ClientData, GameData, IdentityData, default_client_data
from pymc.proto.login.request import (
    encode_authenticated,
    encode_offline,
    marshal_public_key,
    parse_public_key,
)
from pymc.proto.packet import (
    ID_CHUNK_RADIUS_UPDATED,
    ID_NETWORK_SETTINGS,
    ID_PLAY_STATUS,
    ID_RESOURCE_PACK_STACK,
    ID_RESOURCE_PACKS_INFO,
    ID_SERVER_TO_CLIENT_HANDSHAKE,
)
from pymc.proto.packet.chunk_radius_updated import ChunkRadiusUpdated
from pymc.proto.packet.handshake import ClientToServerHandshake
from pymc.proto.packet.login import Login
from pymc.proto.packet.network_settings import NetworkSettings
from pymc.proto.packet.play_status import PlayStatus, STATUS_PLAYER_SPAWN
from pymc.proto.packet.request_chunk_radius import RequestChunkRadius
from pymc.proto.packet.request_network_settings import RequestNetworkSettings
from pymc.proto.packet.resource_packs import (
    PACK_RESPONSE_ALL_PACKS_DOWNLOADED,
    PACK_RESPONSE_COMPLETED,
    ResourcePackClientResponse,
    ResourcePackStack,
    ResourcePacksInfo,
)
from pymc.proto.pool import Packet, server_pool

logger = logging.getLogger(__name__)

# Current protocol version.
PROTOCOL_VERSION = 944


class Dialer:
    """Connects to a Minecraft Bedrock Edition server.

    Attributes:
        identity_data: Player identity (name, UUID, XUID).
        client_data: Client device/skin data.
        protocol_version: Protocol version to negotiate.
        flush_rate: Packet flush interval in seconds.
        chunk_radius: Requested chunk view radius.
    """

    def __init__(
        self,
        *,
        identity_data: IdentityData | None = None,
        client_data: ClientData | None = None,
        protocol_version: int = PROTOCOL_VERSION,
        flush_rate: float = 0.05,
        chunk_radius: int = 16,
        network: Network | None = None,
        legacy_login: bool = False,
        login_chain: str | None = None,
        auth_key: ec.EllipticCurvePrivateKey | None = None,
        multiplayer_token: str = "",
    ) -> None:
        self.identity_data = identity_data or IdentityData(
            display_name="Steve",
            identity=str(uuid.uuid4()),
        )
        self.client_data = client_data or default_client_data()
        self.protocol_version = protocol_version
        self.flush_rate = flush_rate
        self.chunk_radius = chunk_radius
        self.legacy_login = legacy_login
        self.login_chain = login_chain
        self.auth_key = auth_key
        self.multiplayer_token = multiplayer_token
        self._network = network or TCPNetwork()

    async def dial(self, address: str) -> Connection:
        """Connect to a server and complete the login handshake.

        Args:
            address: Server address in "host:port" format.

        Returns:
            An established Connection ready for gameplay packets.
        """
        # Use auth key if provided (must match the key used to request the login chain),
        # otherwise generate a new ECDSA P-384 key pair.
        private_key = self.auth_key or ec.generate_private_key(ec.SECP384R1())

        # Connect transport.
        transport = await self._network.connect(address)

        # Detect NetherNet transport (WebRTC): skip batch header and
        # Minecraft-layer encryption (DTLS handles encryption).
        from pymc.nethernet.conn import NetherNetConn
        is_nethernet = isinstance(transport, NetherNetConn)

        pool = server_pool()
        conn = Connection(
            transport, pool, flush_rate=self.flush_rate,
            use_batch_header=not is_nethernet,
            disable_encryption=is_nethernet,
        )
        await conn.start()

        try:
            await self._handshake(conn, private_key, address)
        except Exception:
            await conn.close()
            raise

        return conn

    async def _handshake(
        self, conn: Connection, private_key: ec.EllipticCurvePrivateKey,
        address: str = "",
    ) -> None:
        """Perform the full client login handshake."""
        # 1. Send RequestNetworkSettings.
        await conn.write_packet_immediate(
            RequestNetworkSettings(client_protocol=self.protocol_version)
        )

        # 2. Wait for NetworkSettings → enable compression.
        pk = await self._expect(conn, NetworkSettings, timeout=10.0)
        conn.enable_compression(pk.compression_algorithm, pk.compression_threshold)

        # 3. Send Login.
        self.client_data.server_address = address
        if not self.client_data.third_party_name:
            self.client_data.third_party_name = self.identity_data.display_name
        if self.login_chain:
            # Authenticated login: enforce Android device data to match
            # the titleId in the Xbox Live JWT chain (same as gophertunnel).
            self.client_data.device_os = 1  # Android
        if self.login_chain:
            connection_request = encode_authenticated(
                self.login_chain, self.client_data, private_key,
                multiplayer_token=self.multiplayer_token,
            )
        else:
            connection_request = encode_offline(
                self.identity_data, self.client_data, private_key,
                legacy=self.legacy_login,
            )
        await conn.write_packet(
            Login(
                client_protocol=self.protocol_version,
                connection_request=connection_request,
            )
        )
        await conn.flush()

        # 4. Wait for ServerToClientHandshake or PlayStatus.
        # Servers with authentication disabled skip the handshake and send
        # PlayStatus directly.
        from pymc.proto.packet.handshake import ServerToClientHandshake
        from pymc.proto.packet.play_status import PlayStatus

        pk = await self._expect_any(
            conn, (ServerToClientHandshake, PlayStatus), timeout=10.0
        )

        if isinstance(pk, ServerToClientHandshake):
            await self._handle_encryption(conn, pk, private_key)

            # 5. Send ClientToServerHandshake.
            await conn.write_packet(ClientToServerHandshake())
            await conn.flush()

            # 5b. Wait for PlayStatus(LoginSuccess).
            pk = await self._expect(conn, PlayStatus, timeout=10.0)
            logger.info("handshake: PlayStatus=%d", pk.status)

        # 5c. Send ClientCacheStatus (required by server before ResourcePacksInfo).
        from pymc.proto.packet.client_cache_status import ClientCacheStatus
        await conn.write_packet(ClientCacheStatus(enabled=False))
        await conn.flush()

        # 6. Handle resource packs.
        await self._handle_resource_packs(conn)

        # 7. Wait for PlayStatus (login success) then request chunks.
        # Note: StartGame and other packets may arrive here.
        # For now we skip to spawn flow.
        await self._wait_for_spawn(conn)

    async def _handle_encryption(
        self,
        conn: Connection,
        pk: "ServerToClientHandshake",
        private_key: ec.EllipticCurvePrivateKey,
    ) -> None:
        """Process ServerToClientHandshake and enable encryption."""
        import base64
        import json

        import jwt as pyjwt

        # Parse JWT without verification to extract server public key and salt.
        token = pk.jwt.decode() if isinstance(pk.jwt, bytes) else pk.jwt
        headers = pyjwt.get_unverified_header(token)
        claims = pyjwt.decode(token, options={"verify_signature": False})

        # Server's public key from x5u header.
        server_pub_key = parse_public_key(headers["x5u"])

        # Salt from claims.
        salt_b64 = claims["salt"].rstrip("=")
        # Pad for standard base64.
        padding = 4 - len(salt_b64) % 4
        if padding < 4:
            salt_b64 += "=" * padding
        salt = base64.b64decode(salt_b64)

        # Compute shared secret via ECDH.
        shared_secret = compute_shared_secret(private_key, server_pub_key)

        # Derive encryption key.
        key = derive_key(salt, shared_secret)

        conn.enable_encryption(key)

    async def _handle_resource_packs(self, conn: Connection) -> None:
        """Handle resource pack negotiation."""
        # Wait for ResourcePacksInfo.
        pk = await self._expect(conn, ResourcePacksInfo, timeout=10.0)

        # Respond: we have all packs (no download).
        await conn.write_packet(
            ResourcePackClientResponse(
                response=PACK_RESPONSE_ALL_PACKS_DOWNLOADED,
            )
        )
        await conn.flush()

        # Wait for ResourcePackStack.
        pk = await self._expect(conn, ResourcePackStack, timeout=10.0)

        # Respond: completed.
        await conn.write_packet(
            ResourcePackClientResponse(response=PACK_RESPONSE_COMPLETED)
        )
        await conn.flush()

    async def _wait_for_spawn(self, conn: Connection) -> None:
        """Wait for the spawn sequence to complete."""
        # Read packets until we get PlayStatus(PLAYER_SPAWN) or
        # ChunkRadiusUpdated, whichever indicates spawn is ready.
        # Send RequestChunkRadius when we receive StartGame (or similar).
        chunk_radius_sent = False

        while True:
            pk = await asyncio.wait_for(conn.read_packet(), timeout=30.0)
            logger.debug("spawn: received %s", type(pk).__name__)

            if isinstance(pk, PlayStatus):
                logger.info("spawn: PlayStatus=%d", pk.status)
                if pk.status == STATUS_PLAYER_SPAWN:
                    break

            elif isinstance(pk, ChunkRadiusUpdated):
                logger.info("spawn: ChunkRadiusUpdated=%d", pk.chunk_radius)

            else:
                # Other packets (StartGame, etc.) - send chunk radius if not yet.
                if not chunk_radius_sent:
                    await conn.write_packet(
                        RequestChunkRadius(
                            chunk_radius=self.chunk_radius,
                            max_chunk_radius=self.chunk_radius,
                        )
                    )
                    await conn.flush()
                    chunk_radius_sent = True

    @staticmethod
    async def _expect(
        conn: Connection,
        packet_type: type[Packet],
        timeout: float = 10.0,
    ) -> Packet:
        """Read packets until we get the expected type."""
        from pymc.proto.packet.disconnect import Disconnect
        from pymc.proto.packet.packet_violation_warning import PacketViolationWarning
        while True:
            pk = await asyncio.wait_for(conn.read_packet(), timeout=timeout)
            if isinstance(pk, packet_type):
                return pk
            if isinstance(pk, Disconnect):
                logger.error("Disconnect while expecting %s: reason=%d message=%s",
                             packet_type.__name__, pk.reason, pk.message)
            elif isinstance(pk, PacketViolationWarning):
                logger.error("PacketViolationWarning while expecting %s: type=%d severity=%d packet=%d ctx=%s",
                             packet_type.__name__, pk.violation_type, pk.severity,
                             pk.violating_packet_id, pk.violation_context)
            else:
                logger.debug("skipping unexpected packet: %s", type(pk).__name__)

    @staticmethod
    async def _expect_any(
        conn: Connection,
        packet_types: tuple[type[Packet], ...],
        timeout: float = 10.0,
    ) -> Packet:
        """Read packets until we get one of the expected types."""
        from pymc.proto.packet.packet_violation_warning import PacketViolationWarning
        from pymc.proto.packet.disconnect import Disconnect
        while True:
            pk = await asyncio.wait_for(conn.read_packet(), timeout=timeout)
            if isinstance(pk, packet_types):
                return pk
            if isinstance(pk, PacketViolationWarning):
                logger.error("PacketViolationWarning: type=%d severity=%d violating_packet=%d context=%s",
                             pk.violation_type, pk.severity, pk.violating_packet_id, pk.violation_context)
            elif isinstance(pk, Disconnect):
                logger.error("Disconnect: reason=%d message=%s", pk.reason, pk.message)
            else:
                logger.debug("skipping unexpected packet: %s", type(pk).__name__)
