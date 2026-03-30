"""Login request encoding and parsing.

Mirrors gophertunnel/minecraft/protocol/login/request.go.
Handles JWT chain creation for both authenticated and offline modes.
"""

from __future__ import annotations

import base64
import json
import struct
import time
import uuid
from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from pymc.proto.login.data import ClientData, IdentityData


def marshal_public_key(key: ec.EllipticCurvePublicKey) -> str:
    """Encode an ECDSA public key to base64 DER format."""
    der = key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(der).decode()


def parse_public_key(b64_data: str) -> ec.EllipticCurvePublicKey:
    """Decode a base64 DER-encoded ECDSA public key."""
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    der = base64.b64decode(b64_data)
    key = load_der_public_key(der)
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise ValueError("key is not an ECDSA public key")
    return key


def encode_offline(
    identity_data: IdentityData,
    client_data: ClientData,
    private_key: ec.EllipticCurvePrivateKey,
    legacy: bool = False,
) -> bytes:
    """Create a self-signed login request for offline mode.

    Mirrors gophertunnel's EncodeOffline. When legacy=False (default,
    for protocol >= 1.26.10), produces the new OIDC multiplayer token
    format. When legacy=True, produces the old extraData chain format.

    Returns the connection_request bytes for the Login packet.
    """
    public_key_b64 = marshal_public_key(private_key.public_key())
    now = int(time.time())

    signer_headers = {"x5u": public_key_b64}
    claims_base = {
        "nbf": now - 21600,  # 6 hours ago
        "exp": now + 21600,  # 6 hours from now
    }

    # Build identity chain JWT with extraData (used by BDS to extract XUID).
    identity_id = identity_data.identity or str(uuid.uuid4())
    identity_claims = {
        **claims_base,
        "extraData": {
            "XUID": identity_data.xuid,
            "identity": identity_id,
            "displayName": identity_data.display_name,
            "titleId": identity_data.title_id,
        },
        "identityPublicKey": public_key_b64,
    }
    chain_jwt = jwt.encode(
        identity_claims, private_key,
        algorithm="ES384", headers=signer_headers,
    )

    if legacy:
        # Legacy format: just {"chain":["<jwt>"]} (pre-1.26.10)
        request_obj = {"chain": [chain_jwt]}
    else:
        # New format: OIDC multiplayer token (1.26.10+)
        # Certificate is a stringified JSON string (double-encoded).
        # Include the identity chain so BDS can extract XUID from extraData.
        token_claims = {
            **claims_base,
            "cpk": public_key_b64,
            "xid": identity_data.xuid,
            "xname": identity_data.display_name,
            "identity": identity_id,
        }
        if identity_data.playfab_id:
            token_claims["mid"] = identity_data.playfab_id
        if identity_data.playfab_title_id:
            token_claims["tid"] = identity_data.playfab_title_id

        token_jwt = jwt.encode(
            token_claims, private_key,
            algorithm="ES384", headers=signer_headers,
        )
        cert_json = json.dumps({"chain": [chain_jwt]}, separators=(",", ":"))
        request_obj = {
            "Certificate": cert_json,  # String, not object
            "AuthenticationType": 2,
            "Token": token_jwt,
        }

    # Client data JWT (RawToken)
    client_dict = _build_client_dict(client_data)
    raw_token = jwt.encode(
        client_dict, private_key,
        algorithm="ES384", headers=signer_headers,
    )

    # Assemble: [request_json_len:le32][request_json][raw_token_len:le32][raw_token]
    request_json = json.dumps(request_obj, separators=(",", ":")).encode()
    raw_token_bytes = raw_token.encode() if isinstance(raw_token, str) else raw_token

    result = bytearray()
    result.extend(struct.pack("<i", len(request_json)))
    result.extend(request_json)
    result.extend(struct.pack("<i", len(raw_token_bytes)))
    result.extend(raw_token_bytes)
    return bytes(result)


def _build_client_dict(client_data: ClientData) -> dict:
    """Build client data claims dictionary for JWT."""
    return {
        "GameVersion": client_data.game_version,
        "ServerAddress": client_data.server_address,
        "LanguageCode": client_data.language_code,
        "DeviceOS": client_data.device_os,
        "DeviceModel": client_data.device_model,
        "DeviceId": client_data.device_id,
        "ClientRandomId": client_data.client_random_id,
        "CurrentInputMode": client_data.current_input_mode,
        "DefaultInputMode": client_data.default_input_mode,
        "GuiScale": client_data.gui_scale,
        "UIProfile": client_data.ui_profile,
        "IsEditorMode": client_data.is_editor_mode,
        "SkinId": client_data.skin_id,
        "SkinData": client_data.skin_data,
        "SkinImageHeight": client_data.skin_image_height,
        "SkinImageWidth": client_data.skin_image_width,
        "SkinResourcePatch": client_data.skin_resource_patch,
        "SkinGeometry": client_data.skin_geometry,
        "SkinGeometryVersion": client_data.skin_geometry_version,
        "SkinColour": client_data.skin_colour,
        "ArmSize": client_data.arm_size,
        "CapeData": client_data.cape_data,
        "CapeId": client_data.cape_id,
        "CapeImageHeight": client_data.cape_image_height,
        "CapeImageWidth": client_data.cape_image_width,
        "CapeOnClassicSkin": client_data.cape_on_classic_skin,
        "PersonaSkin": client_data.persona_skin,
        "PremiumSkin": client_data.premium_skin,
        "TrustedSkin": client_data.trusted_skin,
        "SelfSignedId": client_data.self_signed_id or str(uuid.uuid4()),
        "PlatformOfflineId": client_data.platform_offline_id,
        "PlatformOnlineId": client_data.platform_online_id,
        "ThirdPartyName": client_data.third_party_name,
        "PlayFabId": client_data.playfab_id,
        "CompatibleWithClientSideChunkGen": client_data.compatible_with_client_side_chunk_gen,
        "MaxViewDistance": client_data.max_view_distance,
        "MemoryTier": client_data.memory_tier,
    }


def encode_authenticated(
    login_chain: str,
    client_data: ClientData,
    private_key: ec.EllipticCurvePrivateKey,
    multiplayer_token: str = "",
) -> bytes:
    """Create an authenticated login request using an Xbox Live JWT chain.

    Args:
        login_chain: JWT chain from Minecraft authentication service.
        client_data: Client device/skin data.
        private_key: ECDSA P-384 private key.
        multiplayer_token: Optional multiplayer correlation token.

    Returns:
        connection_request bytes for the Login packet.
    """
    public_key_b64 = marshal_public_key(private_key.public_key())

    # Build client data JWT.
    client_dict = {
        "GameVersion": client_data.game_version,
        "ServerAddress": client_data.server_address,
        "LanguageCode": client_data.language_code,
        "DeviceOS": client_data.device_os,
        "DeviceModel": client_data.device_model,
        "DeviceId": client_data.device_id,
        "ClientRandomId": client_data.client_random_id,
        "CurrentInputMode": client_data.current_input_mode,
        "DefaultInputMode": client_data.default_input_mode,
        "GuiScale": client_data.gui_scale,
        "UIProfile": client_data.ui_profile,
    }

    client_token = jwt.encode(
        client_dict,
        private_key,
        algorithm="ES384",
        headers={"x5u": public_key_b64},
    )
    client_token_bytes = client_token.encode()

    chain_json = login_chain.encode()

    result = bytearray()
    result.extend(struct.pack("<I", len(chain_json)))
    result.extend(chain_json)
    result.extend(struct.pack("<I", len(client_token_bytes)))
    result.extend(client_token_bytes)
    return bytes(result)


@dataclass
class AuthResult:
    """Result of parsing a login request."""
    public_key: ec.EllipticCurvePublicKey | None = None
    xbox_live_authenticated: bool = False


def parse_request(request_data: bytes) -> tuple[IdentityData, ClientData, AuthResult]:
    """Parse a login request and extract identity/client data.

    This is a simplified parser for offline mode. Full authentication
    verification requires OIDC token verification.
    """
    offset = 0

    # Read chain
    chain_len = struct.unpack_from("<I", request_data, offset)[0]
    offset += 4
    chain_json = request_data[offset : offset + chain_len]
    offset += chain_len

    # Read client data JWT
    client_len = struct.unpack_from("<I", request_data, offset)[0]
    offset += 4
    client_jwt = request_data[offset : offset + client_len].decode()

    # Parse chain
    chain_data = json.loads(chain_json)
    chain_tokens = chain_data.get("chain", [])

    identity = IdentityData()
    auth_result = AuthResult()

    # Extract identity from the last chain token (decode without verification for now).
    if chain_tokens:
        last_token = chain_tokens[-1]
        claims = jwt.decode(last_token, options={"verify_signature": False})

        extra_data = claims.get("extraData", {})
        identity.xuid = extra_data.get("XUID", "")
        identity.identity = extra_data.get("identity", "")
        identity.display_name = extra_data.get("displayName", "")
        identity.title_id = extra_data.get("titleId", "")

        pub_key_b64 = claims.get("identityPublicKey", "")
        if pub_key_b64:
            try:
                auth_result.public_key = parse_public_key(pub_key_b64)
            except Exception:
                pass

        # Check for XBL authentication.
        auth_result.xbox_live_authenticated = bool(identity.xuid)

    # Parse client data.
    client = ClientData()
    client_claims = jwt.decode(client_jwt, options={"verify_signature": False})
    client.game_version = client_claims.get("GameVersion", "")
    client.server_address = client_claims.get("ServerAddress", "")
    client.language_code = client_claims.get("LanguageCode", "en_US")
    client.device_os = client_claims.get("DeviceOS", 0)
    client.device_model = client_claims.get("DeviceModel", "")
    client.device_id = client_claims.get("DeviceId", "")
    client.client_random_id = client_claims.get("ClientRandomId", 0)
    client.current_input_mode = client_claims.get("CurrentInputMode", 0)
    client.default_input_mode = client_claims.get("DefaultInputMode", 0)
    client.gui_scale = client_claims.get("GuiScale", 0)
    client.ui_profile = client_claims.get("UIProfile", 0)

    return identity, client, auth_result
