"""npm platform module."""

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


class NpmPlatform(BasePlatform):
    """npm registry user profile checker."""

    name = "npm"
    display_name = "npm"
    base_url = "https://www.npmjs.com"
    url_template = "https://www.npmjs.com/~{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        import time

        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        url = self.get_url(username)
        start_time = time.monotonic()

        try:
            async with session.get(url, headers=self.get_headers()) as response:
                response_time = time.monotonic() - start_time

                if response.status == 200:
                    return PlatformResult(
                        exists=True,
                        url=url,
                        confidence=0.95,
                        response_time=response_time,
                    )
                elif response.status == 404:
                    return PlatformResult(exists=False, confidence=0.99, response_time=response_time)
                else:
                    return PlatformResult(exists=False, error=f"Unexpected status: {response.status}", response_time=response_time)

        except Exception as e:
            return PlatformResult(exists=False, error=str(e), response_time=time.monotonic() - start_time)

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 40:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
