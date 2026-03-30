"""Minecraft Bedrock Edition Realms API client.

Provides async access to the Realms API for listing realms, resolving invite
codes, and obtaining connection addresses.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import aiohttp

from pymc.auth.xbox import XBLToken

REALMS_API_BASE = "https://pocket.realms.minecraft.net"


@dataclass
class Player:
    """A player in a Realm."""

    uuid: str = ""
    name: str = ""
    operator: bool = False
    accepted: bool = False
    online: bool = False
    permission: str = ""


@dataclass
class Realm:
    """A Realm returned from the Realms API."""

    id: int = 0
    remote_subscription_id: str = ""
    owner: str = ""
    owner_uuid: str = ""
    name: str = ""
    motd: str = ""
    default_permission: str = ""
    state: str = ""
    days_left: int = 0
    expired: bool = False
    expired_trial: bool = False
    grace_period: bool = False
    world_type: str = ""
    players: list[Player] = field(default_factory=list)
    max_players: int = 0
    minigame_name: str = ""
    minigame_id: str = ""
    minigame_image: str = ""
    active_slot: int = 0
    member: bool = False
    club_id: int = 0

    _client: RealmsClient | None = field(default=None, repr=False)

    async def address(self) -> str:
        """Get the connection address for this Realm.

        Retries automatically while the Realm is starting up (HTTP 503).
        """
        while True:
            try:
                data = await self._client._request(f"/worlds/{self.id}/join")
                return data["address"]
            except _RealmsHTTPError as e:
                if e.status == 503:
                    await asyncio.sleep(3)
                    continue
                raise

    async def online_players(self) -> list[Player]:
        """Get the players currently online in this Realm.

        Only the Realm owner can call this; others will receive a 403 error.
        """
        data = await self._client._request(f"/worlds/{self.id}")
        return _parse_players(data.get("players", []))


class _RealmsHTTPError(Exception):
    """Internal exception for non-success HTTP responses."""

    def __init__(self, status: int, body: bytes):
        self.status = status
        self.body = body
        super().__init__(f"Realms API error: {status}")


class RealmsClient:
    """Async client for the Minecraft Bedrock Realms API.

    Args:
        xbl_token: An Xbox Live token obtained with relying party
            ``https://pocket.realms.minecraft.net/``.
        session: Optional :class:`aiohttp.ClientSession` to reuse.
    """

    def __init__(
        self,
        xbl_token: XBLToken,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._xbl_token = xbl_token
        self._session = session
        self._own_session = session is None

    async def __aenter__(self) -> RealmsClient:
        if self._own_session:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._own_session and self._session:
            await self._session.close()

    async def realms(self) -> list[Realm]:
        """Get all Realms accessible to the authenticated user."""
        data = await self._request("/worlds")
        result = []
        for s in data.get("servers", []):
            realm = _parse_realm(s)
            realm._client = self
            result.append(realm)
        return result

    async def realm(self, code: str) -> Realm:
        """Get a Realm by its invite code."""
        data = await self._request(f"/worlds/v1/link/{code}")
        realm = _parse_realm(data)
        realm._client = self
        return realm

    async def _request(self, path: str) -> dict:
        """Send an authenticated GET request to the Realms API."""
        if self._own_session and self._session is None:
            self._session = aiohttp.ClientSession()

        headers: dict[str, str] = {
            "User-Agent": "MCPE/UWP",
            "Client-Version": "1.21.0",
        }
        self._xbl_token.set_auth_header(headers)

        async with self._session.get(
            f"{REALMS_API_BASE}{path}", headers=headers
        ) as resp:
            body = await resp.read()
            if resp.status >= 400:
                raise _RealmsHTTPError(resp.status, body)
            return await resp.json(content_type=None)


def _parse_players(raw: list[dict]) -> list[Player]:
    return [
        Player(
            uuid=p.get("uuid", ""),
            name=p.get("Name", p.get("name", "")),
            operator=p.get("operator", False),
            accepted=p.get("accepted", False),
            online=p.get("online", False),
            permission=p.get("permission", ""),
        )
        for p in raw
    ]


def _parse_realm(data: dict) -> Realm:
    return Realm(
        id=data.get("id", 0),
        remote_subscription_id=data.get("remoteSubscriptionID", ""),
        owner=data.get("owner", ""),
        owner_uuid=data.get("ownerUUID", ""),
        name=data.get("name", ""),
        motd=data.get("motd", ""),
        default_permission=data.get("defaultPermission", ""),
        state=data.get("state", ""),
        days_left=data.get("daysLeft", 0),
        expired=data.get("expired", False),
        expired_trial=data.get("expiredTrial", False),
        grace_period=data.get("gracePeriod", False),
        world_type=data.get("worldType", ""),
        players=_parse_players(data.get("players", [])),
        max_players=data.get("maxPlayers", 0),
        minigame_name=data.get("minigameName", ""),
        minigame_id=data.get("minigameId", ""),
        minigame_image=data.get("minigameImage", ""),
        active_slot=data.get("activeSlot", 0),
        member=data.get("member", False),
        club_id=data.get("clubId", 0),
    )
