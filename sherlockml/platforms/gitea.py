"""Gitea platform module."""

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


class GiteaPlatform(BasePlatform):
    """Gitea (Codeberg) code hosting profile checker."""

    name = "gitea"
    display_name = "Codeberg/Gitea"
    base_url = "https://codeberg.org"
    url_template = "https://codeberg.org/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0

    API_URL = "https://codeberg.org/api/v1/users/{username}"

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
                        url=self.get_url(username),
                        metadata={
                            "full_name": data.get("full_name"),
                            "description": data.get("description"),
                            "location": data.get("location"),
                            "website": data.get("website"),
                            "created": data.get("created"),
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
        if not username or len(username) > 40:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
