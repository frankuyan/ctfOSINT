"""Roblox platform module."""

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


class RobloxPlatform(BasePlatform):
    """Roblox gaming platform user checker via API."""

    name = "roblox"
    display_name = "Roblox"
    base_url = "https://www.roblox.com"
    url_template = "https://www.roblox.com/users/profile?username={username}"
    category = PlatformCategory.GAMING
    rate_limit_rpm = 30.0

    API_URL = "https://users.roblox.com/v1/users/search?keyword={username}&limit=10"

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        import time

        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        url = self.API_URL.format(username=username)
        start_time = time.monotonic()

        try:
            async with session.get(url) as response:
                response_time = time.monotonic() - start_time

                if response.status == 200:
                    data = await response.json()
                    users = data.get("data", [])
                    for user in users:
                        if user.get("name", "").lower() == username.lower():
                            return PlatformResult(
                                exists=True,
                                url=f"https://www.roblox.com/users/{user['id']}/profile",
                                metadata={"display_name": user.get("displayName")},
                                confidence=0.99,
                                response_time=response_time,
                            )
                    return PlatformResult(exists=False, confidence=0.9, response_time=response_time)
                else:
                    return PlatformResult(exists=False, error=f"Unexpected status: {response.status}", response_time=response_time)

        except Exception as e:
            return PlatformResult(exists=False, error=str(e), response_time=time.monotonic() - start_time)

    def validate_username(self, username: str) -> bool:
        if not username or len(username) < 3 or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
