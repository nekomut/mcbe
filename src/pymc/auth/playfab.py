"""PlayFab authentication via Xbox Live.

Logs in to PlayFab using an Xbox Live token and returns a session ticket
that can be used to obtain a Minecraft service token.
"""

from __future__ import annotations

import aiohttp

from pymc.auth.xbox import XBLToken

PLAYFAB_RELYING_PARTY = "http://playfab.xboxlive.com/"
PLAYFAB_TITLE_ID = "20CA2"


async def login_with_xbox(
    xbl_token: XBLToken,
    title_id: str = PLAYFAB_TITLE_ID,
    session: aiohttp.ClientSession | None = None,
) -> str:
    """Log in to PlayFab using an Xbox Live token.

    Args:
        xbl_token: An XBL token obtained with relying party
            ``http://playfab.xboxlive.com/``.
        title_id: PlayFab title ID (default ``20CA2``).
        session: Optional aiohttp session to reuse.

    Returns:
        The PlayFab session ticket string.
    """
    url = f"https://{title_id}.playfabapi.com/Client/LoginWithXbox"
    body = {
        "TitleId": title_id,
        "CreateAccount": True,
        "XboxToken": xbl_token.auth_header_value(),
    }

    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            url, json=body, headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(
                    f"PlayFab LoginWithXbox failed ({resp.status}): {text}"
                )
            data = await resp.json(content_type=None)
    finally:
        if own_session:
            await session.close()

    ticket = data.get("data", {}).get("SessionTicket", "")
    if not ticket:
        raise RuntimeError("PlayFab response missing SessionTicket")
    return ticket
