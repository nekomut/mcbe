"""Minecraft Services authentication (Discovery API + MCToken).

Discovers the authorization service endpoint and obtains a service token
(MCToken) needed for NetherNet WebSocket signaling, and a multiplayer token
for OIDC-based login.
"""

from __future__ import annotations

import base64
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiohttp
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

DISCOVERY_URL = "https://client.discovery.minecraft-services.net"
GAME_VERSION = "1.26.12"

logger = logging.getLogger(__name__)


@dataclass
class SignalingInfo:
    """Signaling service info from Discovery API."""

    service_uri: str = ""
    stun_uri: str = ""
    turn_uri: str = ""


@dataclass
class ServiceToken:
    """Token returned by the authorization service."""

    authorization_header: str = ""
    valid_until: str = ""
    treatments: list[str] = field(default_factory=list)
    treatment_context: str = ""

    def valid(self) -> bool:
        if not self.authorization_header:
            return False
        if not self.valid_until:
            return False
        try:
            exp = datetime.fromisoformat(self.valid_until.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < exp
        except (ValueError, TypeError):
            return False


@dataclass
class DiscoveryResult:
    """Parsed Discovery API response."""

    raw: dict = field(default_factory=dict)
    env: str = "prod"

    def _get_service(self, service_name: str) -> dict:
        """Extract a service environment config."""
        import json as _json

        envs = self.raw.get("serviceEnvironments", {})
        svc = envs.get(service_name, {})
        data = svc.get(self.env)
        if data is None:
            raise RuntimeError(
                f"Discovery response missing {service_name}.{self.env}: "
                f"{list(svc.keys())}"
            )
        if isinstance(data, str):
            data = _json.loads(data)
        return data

    @property
    def auth_uri(self) -> str:
        uri = self._get_service("auth").get("serviceUri", "")
        if not uri:
            raise RuntimeError("Discovery auth missing serviceUri")
        return uri

    @property
    def playfab_title_id(self) -> str:
        return self._get_service("auth").get("playfabTitleId", "20CA2")

    @property
    def signaling_info(self) -> SignalingInfo:
        svc = self._get_service("signaling")
        return SignalingInfo(
            service_uri=svc.get("serviceUri", ""),
            stun_uri=svc.get("stunUri", ""),
            turn_uri=svc.get("turnUri", ""),
        )


async def discover(
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
) -> DiscoveryResult:
    """Fetch the Discovery API and resolve the correct environment.

    The environment (prod/stage/dev) is determined from the
    ``supportedEnvironments`` map in the response, matching
    bedrocktool's behaviour.
    """
    url = f"{DISCOVERY_URL}/api/v1.0/discovery/MinecraftPE/builds/{version}"

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.get(
            url, headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Discovery API failed ({resp.status}): {text}")
            data = await resp.json(content_type=None)
    finally:
        if own_session:
            await session.close()

    result = data.get("result", data)

    # Resolve environment from supportedEnvironments (same as bedrocktool).
    supported = result.get("supportedEnvironments", {})
    env_list = supported.get(version, [])
    if env_list:
        env = env_list[0]
    else:
        env = "prod"
    logger.info("Discovery env for %s: %s (supported: %s)", version, env, supported)

    return DiscoveryResult(raw=result, env=env)


# --- Backwards-compatible helpers (used by existing callers) ---


async def _discover_raw(
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
) -> dict:
    """Fetch the raw Discovery API response."""
    d = await discover(version, session)
    return d.raw


def _get_service_env(result: dict, service_name: str, env: str = "prod") -> dict:
    """Extract a service environment from the Discovery result."""
    import json as _json

    envs = result.get("serviceEnvironments", {})
    svc = envs.get(service_name, {})
    data = svc.get(env)
    if data is None:
        raise RuntimeError(
            f"Discovery response missing {service_name}.{env}: {list(envs.keys())}"
        )
    if isinstance(data, str):
        data = _json.loads(data)
    return data


async def discover_auth_uri(
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Discover the authorization service URI."""
    d = await discover(version, session)
    return d.auth_uri


async def discover_signaling(
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
) -> SignalingInfo:
    """Discover the signaling service info (WebSocket URL, STUN/TURN)."""
    d = await discover(version, session)
    return d.signaling_info


async def request_service_token(
    service_uri: str,
    xbox_token: str,
    playfab_title_id: str = "20CA2",
    version: str = GAME_VERSION,
    session: aiohttp.ClientSession | None = None,
) -> ServiceToken:
    """Obtain a service token (MCToken) from the authorization service.

    Args:
        service_uri: Authorization service base URI from Discovery.
        xbox_token: Raw Xbox Live XSTS token string.
        playfab_title_id: PlayFab title ID from Discovery.
        version: Game build version string.
        session: Optional aiohttp session to reuse.

    Returns:
        A :class:`ServiceToken` containing the authorization header JWT.
    """
    url = f"{service_uri}/api/v1.0/session/start"

    body = {
        "device": {
            "applicationType": "MinecraftPE",
            "capabilities": ["RayTracing"],
            "gameVersion": version,
            "id": str(uuid.uuid4()),
            "memory": str(16 * (1 << 30)),
            "platform": "Windows10",
            "playFabTitleId": playfab_title_id.upper(),
            "storePlatform": "uwp.store",
            "treatmentOverrides": None,
            "type": "Windows10",
        },
        "user": {
            "language": "en",
            "languageCode": "en-US",
            "regionCode": "US",
            "token": xbox_token,
            "tokenType": "Xbox",
        },
    }

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"Service token request failed ({resp.status}): {text}"
                )
            data = await resp.json(content_type=None)
    finally:
        if own_session:
            await session.close()

    result = data.get("result", data)
    auth_header = result.get("authorizationHeader", "")
    if not auth_header:
        raise RuntimeError("Service token response missing authorizationHeader")

    return ServiceToken(
        authorization_header=auth_header,
        valid_until=result.get("validUntil", ""),
        treatments=result.get("treatments", []),
        treatment_context=result.get("treatmentContext", ""),
    )


async def request_multiplayer_token(
    service_uri: str,
    service_token: ServiceToken,
    public_key: ec.EllipticCurvePublicKey,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Obtain a multiplayer token (OIDC JWT) from the authorization service.

    The multiplayer token is key-bound — it includes the client's public key
    in the ``cpk`` claim. This token is required as the ``Token`` field in
    the Login packet's connection request for OIDC-based authentication.

    Args:
        service_uri: Authorization service base URI from Discovery.
        service_token: Service token obtained from :func:`request_service_token`.
        public_key: Client's ECDSA public key.
        session: Optional aiohttp session to reuse.

    Returns:
        The signed multiplayer token JWT string.
    """
    url = f"{service_uri}/api/v1.0/multiplayer/session/start"

    pub_der = public_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    body = {"publicKey": base64.b64encode(pub_der).decode()}

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": service_token.authorization_header,
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"Multiplayer token request failed ({resp.status}): {text}"
                )
            data = await resp.json(content_type=None)
    finally:
        if own_session:
            await session.close()

    result = data.get("result", data)
    signed_token = result.get("signedToken", "")
    if not signed_token:
        raise RuntimeError("Multiplayer token response missing signedToken")

    return signed_token
