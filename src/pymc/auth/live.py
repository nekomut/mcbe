"""Microsoft Live Connect authentication via OAuth2 device code flow.

Implements the device auth flow used by Minecraft Bedrock Edition to obtain
an OAuth2 access token from Microsoft Live Connect.
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, field
from typing import IO, Callable

import aiohttp


LIVE_CONNECT_URL = "https://login.live.com/oauth20_connect.srf"
LIVE_TOKEN_URL = "https://login.live.com/oauth20_token.srf"


@dataclass
class Token:
    """OAuth2 token with expiry tracking."""
    access_token: str
    token_type: str
    refresh_token: str
    expiry: float  # Unix timestamp

    def valid(self) -> bool:
        return time.time() < self.expiry - 60  # 1 minute buffer


@dataclass
class Config:
    """Device configuration for MS Live authentication."""
    client_id: str
    device_type: str
    version: str
    user_agent: str


# Predefined device configurations matching Minecraft clients.
ANDROID_CONFIG = Config(
    client_id="0000000048183522",
    device_type="Android",
    version="8.0.0",
    user_agent="XAL Android 2020.07.20200714.000",
)
IOS_CONFIG = Config(
    client_id="000000004c17c01a",
    device_type="iOS",
    version="15.6.1",
    user_agent="XAL iOS 2021.11.20211021.000",
)
WIN32_CONFIG = Config(
    client_id="0000000040159362",
    device_type="Win32",
    version="10.0.25398.4909",
    user_agent="XAL Win32 2021.11.20220411.002",
)
NINTENDO_CONFIG = Config(
    client_id="00000000441cc96b",
    device_type="Nintendo",
    version="0.0.0",
    user_agent="XAL",
)
PLAYSTATION_CONFIG = Config(
    client_id="000000004827c78e",
    device_type="Playstation",
    version="10.0.0",
    user_agent="XAL",
)


# Global server time delta for signed requests.
_server_time_delta: float = 0.0


def update_server_time(headers: dict[str, str]) -> None:
    """Update server time offset from response headers."""
    global _server_time_delta
    from email.utils import parsedate_to_datetime
    date_str = headers.get("Date", "")
    if not date_str:
        return
    try:
        server_time = parsedate_to_datetime(date_str).timestamp()
        _server_time_delta = server_time - time.time()
    except Exception:
        pass


def server_time() -> float:
    """Return estimated server time as Unix timestamp."""
    return time.time() + _server_time_delta


async def request_live_token(
    config: Config | None = None,
    writer: IO[str] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> Token:
    """Request a Live Connect token using the device auth flow.

    Prints an authentication URL and code, then polls until the user completes
    authentication.

    Args:
        config: Device config. Defaults to ANDROID_CONFIG.
        writer: Where to print auth instructions. Defaults to sys.stdout.
        session: HTTP session. Creates one if not provided.

    Returns:
        A valid OAuth2 Token.
    """
    if config is None:
        config = ANDROID_CONFIG
    if writer is None:
        writer = sys.stdout

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        device_auth = await _start_device_auth(session, config)
        writer.write(
            f"Authenticate at {device_auth['verification_uri']} "
            f"using the code {device_auth['user_code']}.\n"
        )
        writer.flush()

        interval = device_auth.get("interval", 5)
        while True:
            await asyncio.sleep(interval)
            token = await _poll_device_auth(session, config, device_auth["device_code"])
            if token is not None:
                writer.write("Authentication successful.\n")
                writer.flush()
                return token
    finally:
        if own_session:
            await session.close()


async def refresh_token(
    token: Token,
    config: Config | None = None,
    session: aiohttp.ClientSession | None = None,
) -> Token:
    """Refresh an expired OAuth2 token.

    Args:
        token: The token to refresh.
        config: Device config. Defaults to ANDROID_CONFIG.
        session: HTTP session. Creates one if not provided.

    Returns:
        A new valid OAuth2 Token.
    """
    if config is None:
        config = ANDROID_CONFIG

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            LIVE_TOKEN_URL,
            data={
                "client_id": config.client_id,
                "scope": "service::user.auth.xboxlive.com::MBI_SSL",
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
        ) as resp:
            update_server_time(dict(resp.headers))
            data = await resp.json(content_type=None)
            if resp.status != 200:
                raise RuntimeError(f"token refresh failed: {data.get('error', resp.status)}")
            return Token(
                access_token=data["access_token"],
                token_type=data["token_type"],
                refresh_token=data["refresh_token"],
                expiry=time.time() + data["expires_in"],
            )
    finally:
        if own_session:
            await session.close()


async def _start_device_auth(
    session: aiohttp.ClientSession, config: Config
) -> dict:
    async with session.post(
        LIVE_CONNECT_URL,
        data={
            "client_id": config.client_id,
            "scope": "service::user.auth.xboxlive.com::MBI_SSL",
            "response_type": "device_code",
        },
    ) as resp:
        if resp.status != 200:
            raise RuntimeError(f"device auth failed: {resp.status}")
        return await resp.json(content_type=None)


async def _poll_device_auth(
    session: aiohttp.ClientSession, config: Config, device_code: str
) -> Token | None:
    async with session.post(
        LIVE_TOKEN_URL,
        data={
            "client_id": config.client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
        },
    ) as resp:
        update_server_time(dict(resp.headers))
        data = await resp.json(content_type=None)
        error = data.get("error", "")
        if error == "authorization_pending":
            return None
        if error:
            raise RuntimeError(f"device auth error: {error}: {data.get('error_description', '')}")
        return Token(
            access_token=data["access_token"],
            token_type=data["token_type"],
            refresh_token=data["refresh_token"],
            expiry=time.time() + data["expires_in"],
        )
