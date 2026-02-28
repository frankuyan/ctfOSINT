"""Stack Overflow platform module."""

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


class StackOverflowPlatform(BasePlatform):
    """Stack Overflow user search via API."""

    name = "stackoverflow"
    display_name = "Stack Overflow"
    base_url = "https://stackoverflow.com"
    url_template = "https://stackoverflow.com/users?tab=accounts&SearchTerm={username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 30.0

    API_URL = "https://api.stackexchange.com/2.3/users"

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Search for user via Stack Exchange API."""
        import time

        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        url = f"{self.API_URL}?inname={username}&site=stackoverflow&pagesize=1"

        start_time = time.monotonic()

        try:
            async with session.get(url) as response:
                response_time = time.monotonic() - start_time

                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])

                    if items:
                        user = items[0]
                        if user.get("display_name", "").lower() == username.lower():
                            return PlatformResult(
                                exists=True,
                                url=user.get("link", self.get_url(username)),
                                metadata={
                                    "display_name": user.get("display_name"),
                                    "reputation": user.get("reputation"),
                                    "location": user.get("location"),
                                    "creation_date": user.get("creation_date"),
                                },
                                confidence=0.95,
                                response_time=response_time,
                            )

                    return PlatformResult(
                        exists=False,
                        confidence=0.8,
                        response_time=response_time,
                    )
                else:
                    return PlatformResult(
                        exists=False,
                        error=f"Unexpected status: {response.status}",
                        response_time=response_time,
                    )

        except Exception as e:
            return PlatformResult(
                exists=False,
                error=str(e),
                response_time=time.monotonic() - start_time,
            )

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_._ -]+$', username))
