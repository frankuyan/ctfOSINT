"""Docker Hub platform module."""

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


class DockerHubPlatform(BasePlatform):
    """Docker Hub user profile checker via API."""

    name = "dockerhub"
    display_name = "Docker Hub"
    base_url = "https://hub.docker.com"
    url_template = "https://hub.docker.com/u/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0

    API_URL = "https://hub.docker.com/v2/users/{username}/"

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
                            "location": data.get("location"),
                            "company": data.get("company"),
                            "date_joined": data.get("date_joined"),
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
