"""Keybase platform module."""

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


class KeybasePlatform(BasePlatform):
    """Keybase platform with API checking - high CTF relevance."""
    
    name = "keybase"
    display_name = "Keybase"
    base_url = "https://keybase.io"
    url_template = "https://keybase.io/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    
    API_URL = "https://keybase.io/_/api/1.0/user/lookup.json"
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check Keybase user via API."""
        import time
        
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")
        
        url = f"{self.API_URL}?username={username}"
        
        start_time = time.monotonic()
        
        try:
            async with session.get(url) as response:
                response_time = time.monotonic() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status", {}).get("code") != 0:
                        return PlatformResult(
                            exists=False,
                            confidence=0.99,
                            response_time=response_time,
                        )
                    
                    user = data.get("them", {})
                    basics = user.get("basics", {})
                    profile = user.get("profile", {})
                    
                    return PlatformResult(
                        exists=True,
                        url=self.get_url(username),
                        metadata={
                            "username": basics.get("username"),
                            "full_name": profile.get("full_name"),
                            "location": profile.get("location"),
                            "bio": profile.get("bio"),
                            "proofs": [
                                p.get("proof_type") 
                                for p in user.get("proofs_summary", {}).get("all", [])
                            ],
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
        """Validate Keybase username format."""
        if not username or len(username) > 16:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
