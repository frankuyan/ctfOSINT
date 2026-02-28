"""Lobsters platform module."""

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


class LobstersPlatform(BasePlatform):
    """Lobsters tech news community profile checker."""

    name = "lobsters"
    display_name = "Lobsters"
    base_url = "https://lobste.rs"
    url_template = "https://lobste.rs/u/{username}"
    category = PlatformCategory.NEWS
    rate_limit_rpm = 30.0

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        import time

        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        url = f"{self.get_url(username)}.json"
        start_time = time.monotonic()

        try:
            async with session.get(url) as response:
                response_time = time.monotonic() - start_time

                if response.status == 200:
                    data = await response.json()
                    return PlatformResult(
                        exists=True,
                        url=self.get_url(username),
                        metadata={
                            "karma": data.get("karma"),
                            "about": data.get("about"),
                            "created_at": data.get("created_at"),
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
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
