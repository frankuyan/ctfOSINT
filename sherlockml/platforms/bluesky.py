"""Bluesky platform module."""

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


class BlueskyPlatform(BasePlatform):
    """Bluesky social network profile checker via API."""

    name = "bluesky"
    display_name = "Bluesky"
    base_url = "https://bsky.app"
    url_template = "https://bsky.app/profile/{username}.bsky.social"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0

    API_URL = "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile"

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        import time

        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        handle = f"{username}.bsky.social"
        url = f"{self.API_URL}?actor={handle}"
        start_time = time.monotonic()

        try:
            async with session.get(url) as response:
                response_time = time.monotonic() - start_time

                if response.status == 200:
                    data = await response.json()
                    return PlatformResult(
                        exists=True,
                        url=f"https://bsky.app/profile/{handle}",
                        metadata={
                            "display_name": data.get("displayName"),
                            "description": data.get("description"),
                            "followers_count": data.get("followersCount"),
                            "follows_count": data.get("followsCount"),
                            "posts_count": data.get("postsCount"),
                        },
                        confidence=0.99,
                        response_time=response_time,
                    )
                elif response.status == 400:
                    return PlatformResult(exists=False, confidence=0.99, response_time=response_time)
                else:
                    return PlatformResult(exists=False, error=f"Unexpected status: {response.status}", response_time=response_time)

        except Exception as e:
            return PlatformResult(exists=False, error=str(e), response_time=time.monotonic() - start_time)

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
