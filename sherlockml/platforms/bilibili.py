"""Bilibili platform module."""

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


class BilibiliPlatform(BasePlatform):
    """Bilibili (bilibili.com) video platform checker.

    Uses the Bilibili search API to look up users by name.
    """

    name = "bilibili"
    display_name = "Bilibili"
    base_url = "https://www.bilibili.com"
    url_template = "https://space.bilibili.com/{username}"
    category = PlatformCategory.VIDEO
    rate_limit_rpm = 30.0

    _SEARCH_API = "https://api.bilibili.com/x/web-interface/card?mid={username}"

    def validate_username(self, username: str) -> bool:
        # Bilibili user IDs are numeric
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^\d+$', username))

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        import time

        if not self.validate_username(username):
            return PlatformResult(
                exists=False,
                error=f"Invalid username format for {self.name}",
            )

        url = self._SEARCH_API.format(username=username)
        headers = self.get_headers()
        start = time.monotonic()

        try:
            async with session.get(url, headers=headers) as resp:
                elapsed = time.monotonic() - start
                if resp.status != 200:
                    return PlatformResult(
                        exists=False, confidence=0.3, response_time=elapsed,
                        error=f"Unexpected status code: {resp.status}",
                    )
                data = await resp.json(content_type=None)
                if data.get("code") == 0 and data.get("data", {}).get("card"):
                    card = data["data"]["card"]
                    return PlatformResult(
                        exists=True,
                        url=self.get_url(username),
                        confidence=0.95,
                        response_time=elapsed,
                        metadata={
                            "display_name": card.get("name"),
                            "fans": card.get("fans"),
                        },
                    )
                return PlatformResult(
                    exists=False, confidence=0.9, response_time=elapsed,
                )
        except Exception as e:
            return PlatformResult(
                exists=False, error=str(e),
                response_time=time.monotonic() - start,
            )
