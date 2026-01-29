"""Instagram platform module."""

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


class InstagramPlatform(HTTPCheckPlatform):
    """Instagram platform checker."""
    
    name = "instagram"
    display_name = "Instagram"
    base_url = "https://instagram.com"
    url_template = "https://instagram.com/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 20.0
    check_method = "GET"
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check Instagram username."""
        import time
        
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")
        
        url = self.get_url(username)
        headers = self.get_headers()
        
        start_time = time.monotonic()
        
        try:
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                response_time = time.monotonic() - start_time
                
                if response.status == 200:
                    text = await response.text()
                    
                    # Check for page not found indicators
                    if "Sorry, this page isn't available" in text:
                        return PlatformResult(
                            exists=False,
                            confidence=0.95,
                            response_time=response_time,
                        )
                    else:
                        return PlatformResult(
                            exists=True,
                            url=url,
                            confidence=0.9,
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
                        response_time=response_time,
                    )
                    
        except Exception as e:
            return PlatformResult(
                exists=False,
                error=str(e),
                response_time=time.monotonic() - start_time,
            )
    
    def validate_username(self, username: str) -> bool:
        """Validate Instagram username format."""
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
