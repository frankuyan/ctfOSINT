"""Chess.com platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    BasePlatform,
    PlatformCategory,
    PlatformResult,
)

if TYPE_CHECKING:
    import aiohttp


class ChessComPlatform(BasePlatform):
    """Chess.com player profile checker via API."""

    name = "chesscom"
    display_name = "Chess.com"
    base_url = "https://chess.com"
    url_template = "https://chess.com/member/{username}"
    category = PlatformCategory.GAMING
    rate_limit_rpm = 30.0

    API_URL = "https://api.chess.com/pub/player/{username}"

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        import time

        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        url = self.API_URL.format(username=username.lower())
        start_time = time.monotonic()

        try:
            async with session.get(url) as response:
                response_time = time.monotonic() - start_time

                if response.status == 200:
                    data = await response.json()
                    return PlatformResult(
                        exists=True,
                        url=data.get("url", self.get_url(username)),
                        metadata={
                            "name": data.get("name"),
                            "location": data.get("location"),
                            "followers": data.get("followers"),
                            "joined": data.get("joined"),
                            "status": data.get("status"),
                        },
                        confidence=0.99,
                        response_time=response_time,
                    )
                elif response.status == 404:
                    return PlatformResult(exists=False, confidence=0.99, response_time=response_time)
                else:
                    return PlatformResult(exists=False, error=f"Unexpected status: {response.status}", response_time=response_time)

        except Exception as e:
            return PlatformResult(exists=False, error=str(e), response_time=time.monotonic() - start_time)

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 25:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
