"""Xbox Live authentication.

Handles device token acquisition and XSTS token exchange using ECDSA P-256
signed requests, matching the Xbox Live SISU authorization flow.
"""

from __future__ import annotations

import base64
import hashlib
import struct
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import aiohttp
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDSA,
    SECP256R1,
    EllipticCurvePrivateKey,
)
from cryptography.hazmat.primitives.hashes import SHA256

from pymc.auth.live import Config, Token, server_time, update_server_time, ANDROID_CONFIG


DEVICE_AUTH_URL = "https://device.auth.xboxlive.com/device/authenticate"
SISU_AUTHORIZE_URL = "https://sisu.xboxlive.com/authorize"

# Windows epoch offset from Unix epoch (in seconds)
_WINDOWS_EPOCH_OFFSET = 11644473600


@dataclass
class XBLToken:
    """Xbox Live authorization token."""
    token: str = ""
    user_hash: str = ""
    gamer_tag: str = ""
    xuid: str = ""
    issue_instant: str = ""
    not_after: str = ""

    def valid(self) -> bool:
        if not self.not_after:
            return False
        from datetime import datetime, timezone
        try:
            expiry = datetime.fromisoformat(self.not_after.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < expiry
        except Exception:
            return False

    def auth_header_value(self) -> str:
        return f"XBL3.0 x={self.user_hash};{self.token}"

    def set_auth_header(self, headers: dict[str, str]) -> None:
        headers["Authorization"] = self.auth_header_value()


@dataclass
class _DeviceToken:
    """Internal device token with proof key."""
    token: str
    issue_instant: str
    not_after: str
    proof_key: EllipticCurvePrivateKey


def _generate_proof_key() -> EllipticCurvePrivateKey:
    """Generate an ECDSA P-256 private key for proof of possession."""
    return ec.generate_private_key(SECP256R1())


def _public_key_xy(key: EllipticCurvePrivateKey) -> tuple[bytes, bytes]:
    """Extract the X and Y coordinates from an EC public key as 32-byte values."""
    pub = key.public_key()
    numbers = pub.public_numbers()
    x = numbers.x.to_bytes(32, "big")
    y = numbers.y.to_bytes(32, "big")
    return x, y


def _proof_key_json(key: EllipticCurvePrivateKey) -> dict[str, str]:
    """Build the ProofKey JSON object for Xbox Live requests."""
    x, y = _public_key_xy(key)
    return {
        "crv": "P-256",
        "alg": "ES256",
        "use": "sig",
        "kty": "EC",
        "x": base64.urlsafe_b64encode(x).rstrip(b"=").decode(),
        "y": base64.urlsafe_b64encode(y).rstrip(b"=").decode(),
    }


def _windows_timestamp(unix_time: float) -> int:
    """Convert Unix timestamp to Windows file time (100-nanosecond intervals)."""
    return int((unix_time + _WINDOWS_EPOCH_OFFSET) * 10_000_000)


def _sign_request(
    method: str,
    path: str,
    body: bytes,
    authorization: str,
    key: EllipticCurvePrivateKey,
) -> str:
    """Sign an Xbox Live request and return the Signature header value."""
    current_time = _windows_timestamp(server_time())

    h = hashlib.sha256()

    # Signature policy version (0,0,0,1) + null byte
    policy = struct.pack(">I", 1) + b"\x00"
    # Timestamp (big-endian int64) + null byte
    ts = struct.pack(">q", current_time) + b"\x00"
    h.update(policy)
    h.update(ts)

    # Method + null
    h.update(method.encode() + b"\x00")
    # Path + null
    h.update(path.encode() + b"\x00")
    # Authorization + null
    h.update(authorization.encode() + b"\x00")
    # Body + null
    h.update(body + b"\x00")

    digest = h.digest()

    # Sign with ECDSA
    der_sig = key.sign(digest, ec.ECDSA(utils.Prehashed(SHA256())))
    r, s = utils.decode_dss_signature(der_sig)

    # Encode r and s as 32-byte zero-padded big-endian
    sig_bytes = r.to_bytes(32, "big") + s.to_bytes(32, "big")

    # Prepend policy version (4 bytes) + timestamp (8 bytes)
    header_bytes = struct.pack(">I", 1) + struct.pack(">q", current_time) + sig_bytes
    return base64.b64encode(header_bytes).decode()


async def request_device_token(
    config: Config | None = None,
    session: aiohttp.ClientSession | None = None,
) -> _DeviceToken:
    """Request a device token from Xbox Live.

    Args:
        config: Device configuration. Defaults to ANDROID_CONFIG.
        session: HTTP session.

    Returns:
        A _DeviceToken with proof key.
    """
    if config is None:
        config = ANDROID_CONFIG

    key = _generate_proof_key()
    body = {
        "RelyingParty": "http://auth.xboxlive.com",
        "TokenType": "JWT",
        "Properties": {
            "AuthMethod": "ProofOfPossession",
            "Id": "{" + str(uuid4()) + "}",
            "DeviceType": config.device_type,
            "Version": config.version,
            "ProofKey": _proof_key_json(key),
        },
    }

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        import json
        body_bytes = json.dumps(body).encode()
        path = "/device/authenticate"
        sig = _sign_request("POST", path, body_bytes, "", key)

        async with session.post(
            DEVICE_AUTH_URL,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Signature": sig,
                "x-xbl-contract-version": "1",
            },
        ) as resp:
            update_server_time(dict(resp.headers))
            if resp.status != 200:
                err_body = await resp.text()
                raise RuntimeError(f"device auth failed: {resp.status} {err_body}")
            data = await resp.json(content_type=None)
            return _DeviceToken(
                token=data["Token"],
                issue_instant=data.get("IssueInstant", ""),
                not_after=data.get("NotAfter", ""),
                proof_key=key,
            )
    finally:
        if own_session:
            await session.close()


async def request_xbl_token(
    live_token: Token,
    relying_party: str,
    config: Config | None = None,
    session: aiohttp.ClientSession | None = None,
) -> XBLToken:
    """Request an Xbox Live XSTS token.

    Args:
        live_token: Valid Microsoft Live OAuth2 token.
        relying_party: The relying party URL (e.g. "https://multiplayer.minecraft.net/").
        config: Device configuration. Defaults to ANDROID_CONFIG.
        session: HTTP session.

    Returns:
        An XBLToken for use in Minecraft authentication.
    """
    if config is None:
        config = ANDROID_CONFIG
    if not live_token.valid():
        raise RuntimeError("live token is no longer valid")

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        device = await request_device_token(config, session)

        import json
        body = {
            "AccessToken": "t=" + live_token.access_token,
            "AppId": config.client_id,
            "DeviceToken": device.token,
            "Sandbox": "RETAIL",
            "UseModernGamertag": True,
            "SiteName": "user.auth.xboxlive.com",
            "RelyingParty": relying_party,
            "ProofKey": _proof_key_json(device.proof_key),
        }
        body_bytes = json.dumps(body).encode()
        path = "/authorize"
        sig = _sign_request("POST", path, body_bytes, "", device.proof_key)

        async with session.post(
            SISU_AUTHORIZE_URL,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Signature": sig,
                "x-xbl-contract-version": "1",
            },
        ) as resp:
            update_server_time(dict(resp.headers))
            if resp.status != 200:
                error_code = resp.headers.get("x-err", "")
                msg = _parse_xbox_error(error_code) if error_code else str(resp.status)
                raise RuntimeError(f"XBL auth failed: {msg}")
            data = await resp.json(content_type=None)
            auth = data.get("AuthorizationToken", {})
            user_info = auth.get("DisplayClaims", {}).get("xui", [{}])[0]
            return XBLToken(
                token=auth.get("Token", ""),
                user_hash=user_info.get("uhs", ""),
                gamer_tag=user_info.get("gtg", ""),
                xuid=user_info.get("xid", ""),
                issue_instant=auth.get("IssueInstant", ""),
                not_after=auth.get("NotAfter", ""),
            )
    finally:
        if own_session:
            await session.close()


def _parse_xbox_error(code: str) -> str:
    errors = {
        "2148916227": "Account banned by Xbox.",
        "2148916229": "Account restricted - guardian permission needed.",
        "2148916233": "No Xbox profile - create one at https://signup.live.com/signup",
        "2148916234": "Xbox Terms of Service not accepted.",
        "2148916235": "Region not authorized by Xbox.",
        "2148916236": "Proof of age required.",
        "2148916237": "Playtime limit reached.",
        "2148916238": "Account under 18 - must be added to family.",
    }
    return errors.get(code, f"unknown error code: {code}")
