"""Bitbucket platform module."""

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


class BitbucketPlatform(BasePlatform):
    """Bitbucket user profile checker via API."""

    name = "bitbucket"
    display_name = "Bitbucket"
    base_url = "https://bitbucket.org"
    url_template = "https://bitbucket.org/{username}/"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0

    API_URL = "https://api.bitbucket.org/2.0/users/{username}"

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
                    return PlatformResult(
                        exists=True,
                        url=data.get("links", {}).get("html", {}).get("href", self.get_url(username)),
                        metadata={
                            "display_name": data.get("display_name"),
                            "created_on": data.get("created_on"),
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
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
