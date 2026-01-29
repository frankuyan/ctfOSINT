"""Hacker News platform module."""

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


class HackerNewsPlatform(BasePlatform):
    """Hacker News platform with API checking."""
    
    name = "hackernews"
    display_name = "Hacker News"
    base_url = "https://news.ycombinator.com"
    url_template = "https://news.ycombinator.com/user?id={username}"
    category = PlatformCategory.NEWS
    rate_limit_rpm = 60.0
    
    API_URL = "https://hacker-news.firebaseio.com/v0/user/{username}.json"
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check HN user via Firebase API."""
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
                    
                    if data is None:
                        return PlatformResult(
                            exists=False,
                            confidence=0.99,
                            response_time=response_time,
                        )
                    
                    return PlatformResult(
                        exists=True,
                        url=self.get_url(username),
                        metadata={
                            "karma": data.get("karma"),
                            "about": data.get("about"),
                            "created": data.get("created"),
                            "submitted_count": len(data.get("submitted", [])),
                        },
                        confidence=0.99,
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
        """Validate HN username format."""
        if not username or len(username) > 15:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
