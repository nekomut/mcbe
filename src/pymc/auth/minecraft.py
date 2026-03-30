"""Minecraft authentication - JWT chain request.

Requests a Minecraft JWT chain from the multiplayer authentication endpoint
using an Xbox Live token and the client's ECDSA private key.
"""

from __future__ import annotations

import base64

import aiohttp
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from pymc.auth.xbox import XBLToken

MINECRAFT_AUTH_URL = "https://multiplayer.minecraft.net/authentication"
CURRENT_VERSION = "1.26.10"


async def request_minecraft_chain(
    xbl_token: XBLToken,
    private_key: EllipticCurvePrivateKey,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Request a Minecraft JWT chain for use in the Login packet.

    Args:
        xbl_token: Valid Xbox Live XSTS token.
        private_key: Client's ECDSA P-256 private key (used later for encryption).
        session: HTTP session.

    Returns:
        Raw JWT chain string from the Minecraft auth endpoint.
    """
    # Serialize the public key in SubjectPublicKeyInfo (PKIX/DER) format
    pub_der = private_key.public_key().public_bytes(
        Encoding.DER,
        PublicFormat.SubjectPublicKeyInfo,
    )
    identity_public_key = base64.b64encode(pub_der).decode()

    body = f'{{"identityPublicKey":"{identity_public_key}"}}'

    headers: dict[str, str] = {
        "User-Agent": "MCPE/Android",
        "Client-Version": CURRENT_VERSION,
        "Content-Type": "application/json",
    }
    xbl_token.set_auth_header(headers)

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            MINECRAFT_AUTH_URL,
            data=body.encode(),
            headers=headers,
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Minecraft auth failed: {resp.status}")
            return await resp.text()
    finally:
        if own_session:
            await session.close()
