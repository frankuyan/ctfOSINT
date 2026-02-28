"""Codeforces platform module."""

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


class CodeforcesPlatform(BasePlatform):
    """Codeforces competitive programming profile checker via API."""

    name = "codeforces"
    display_name = "Codeforces"
    base_url = "https://codeforces.com"
    url_template = "https://codeforces.com/profile/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 30.0

    API_URL = "https://codeforces.com/api/user.info?handles={username}"

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
                    if data.get("status") == "OK" and data.get("result"):
                        user = data["result"][0]
                        return PlatformResult(
                            exists=True,
                            url=self.get_url(username),
                            metadata={
                                "rating": user.get("rating"),
                                "max_rating": user.get("maxRating"),
                                "rank": user.get("rank"),
                                "organization": user.get("organization"),
                            },
                            confidence=0.99,
                            response_time=response_time,
                        )
                    return PlatformResult(exists=False, confidence=0.95, response_time=response_time)
                elif response.status == 400:
                    return PlatformResult(exists=False, confidence=0.99, response_time=response_time)
                else:
                    return PlatformResult(exists=False, error=f"Unexpected status: {response.status}", response_time=response_time)

        except Exception as e:
            return PlatformResult(exists=False, error=str(e), response_time=time.monotonic() - start_time)

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 24:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
