"""GitLab platform module."""

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


class GitLabPlatform(BasePlatform):
    """GitLab platform with API checking."""
    
    name = "gitlab"
    display_name = "GitLab"
    base_url = "https://gitlab.com"
    url_template = "https://gitlab.com/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    
    API_URL = "https://gitlab.com/api/v4/users"
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check GitLab user via API."""
        import time
        
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")
        
        url = f"{self.API_URL}?username={username}"
        headers = self.get_headers()
        
        start_time = time.monotonic()
        
        try:
            async with session.get(url, headers=headers) as response:
                response_time = time.monotonic() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    if not data:
                        return PlatformResult(
                            exists=False,
                            confidence=0.99,
                            response_time=response_time,
                        )
                    
                    user = data[0]
                    return PlatformResult(
                        exists=True,
                        url=user.get("web_url", self.get_url(username)),
                        metadata={
                            "name": user.get("name"),
                            "username": user.get("username"),
                            "state": user.get("state"),
                            "avatar_url": user.get("avatar_url"),
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
        """Validate GitLab username format."""
        if not username or len(username) > 255:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
