"""Twitter/X platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
    PlatformResult,
)

if TYPE_CHECKING:
    import aiohttp


class TwitterPlatform(HTTPCheckPlatform):
    """Twitter/X platform checker."""
    
    name = "twitter"
    display_name = "Twitter/X"
    base_url = "https://twitter.com"
    url_template = "https://twitter.com/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0  # Conservative due to blocking
    check_method = "GET"
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check Twitter username - uses page scraping since API requires auth."""
        import time
        
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")
        
        url = self.get_url(username)
        headers = self.get_headers()
        
        start_time = time.monotonic()
        
        try:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                response_time = time.monotonic() - start_time
                
                # Twitter often returns 200 even for non-existent users
                # Need to check page content
                if response.status == 200:
                    text = await response.text()
                    
                    # Check for suspended account or non-existent indicators
                    if "This account doesn't exist" in text:
                        return PlatformResult(
                            exists=False,
                            confidence=0.95,
                            response_time=response_time,
                        )
                    elif "Account suspended" in text:
                        return PlatformResult(
                            exists=True,
                            url=url,
                            metadata={"status": "suspended"},
                            confidence=0.9,
                            response_time=response_time,
                        )
                    else:
                        return PlatformResult(
                            exists=True,
                            url=url,
                            confidence=0.85,
                            response_time=response_time,
                        )
                        
                elif response.status == 404:
                    return PlatformResult(
                        exists=False,
                        confidence=0.95,
                        response_time=response_time,
                    )
                else:
                    return PlatformResult(
                        exists=False,
                        error=f"Unexpected status: {response.status}",
                        confidence=0.3,
                        response_time=response_time,
                    )
                    
        except Exception as e:
            return PlatformResult(
                exists=False,
                error=str(e),
                response_time=time.monotonic() - start_time,
            )
    
    def validate_username(self, username: str) -> bool:
        """Validate Twitter username format."""
        if not username or len(username) > 15:
            return False
        
        # Twitter: alphanumeric and underscores only
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
