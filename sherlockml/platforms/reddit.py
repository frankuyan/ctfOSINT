"""Reddit platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    BasePlatform,
    PlatformCategory,
    PlatformMetadata,
    PlatformResult,
)

if TYPE_CHECKING:
    import aiohttp


class RedditPlatform(BasePlatform):
    """Reddit platform with API-based checking."""
    
    name = "reddit"
    display_name = "Reddit"
    base_url = "https://reddit.com"
    url_template = "https://reddit.com/user/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check Reddit user via JSON API."""
        import time
        
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")
        
        # Reddit's user about JSON endpoint
        url = f"https://www.reddit.com/user/{username}/about.json"
        headers = self.get_headers()
        
        start_time = time.monotonic()
        
        try:
            async with session.get(url, headers=headers) as response:
                response_time = time.monotonic() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    user_data = data.get("data", {})
                    
                    return PlatformResult(
                        exists=True,
                        url=self.get_url(username),
                        metadata={
                            "name": user_data.get("name"),
                            "created_utc": user_data.get("created_utc"),
                            "link_karma": user_data.get("link_karma"),
                            "comment_karma": user_data.get("comment_karma"),
                            "is_gold": user_data.get("is_gold"),
                            "verified": user_data.get("verified"),
                        },
                        confidence=0.99,
                        response_time=response_time,
                    )
                elif response.status == 404:
                    return PlatformResult(
                        exists=False,
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
        """Validate Reddit username format."""
        if not username or len(username) < 3 or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
