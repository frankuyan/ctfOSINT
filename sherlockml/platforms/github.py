"""GitHub platform module."""

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


class GitHubPlatform(BasePlatform):
    """GitHub platform with deep profile extraction."""
    
    name = "github"
    display_name = "GitHub"
    base_url = "https://github.com"
    url_template = "https://github.com/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    
    # GitHub API endpoints
    API_BASE = "https://api.github.com"
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check if GitHub user exists using API."""
        import time
        
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")
        
        url = f"{self.API_BASE}/users/{username}"
        headers = self.get_headers()
        headers["Accept"] = "application/vnd.github.v3+json"
        
        start_time = time.monotonic()
        
        try:
            async with session.get(url, headers=headers) as response:
                response_time = time.monotonic() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return PlatformResult(
                        exists=True,
                        url=data.get("html_url", self.get_url(username)),
                        metadata={
                            "name": data.get("name"),
                            "bio": data.get("bio"),
                            "location": data.get("location"),
                            "email": data.get("email"),
                            "company": data.get("company"),
                            "blog": data.get("blog"),
                            "public_repos": data.get("public_repos"),
                            "followers": data.get("followers"),
                            "following": data.get("following"),
                            "created_at": data.get("created_at"),
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
                elif response.status == 403:
                    return PlatformResult(
                        exists=False,
                        error="Rate limited by GitHub API",
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
    
    async def extract_metadata(
        self,
        url: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformMetadata:
        """Extract detailed metadata from GitHub profile."""
        # Extract username from URL
        match = re.match(r"https://github\.com/([^/]+)", url)
        if not match:
            return PlatformMetadata()
        
        username = match.group(1)
        api_url = f"{self.API_BASE}/users/{username}"
        headers = self.get_headers()
        headers["Accept"] = "application/vnd.github.v3+json"
        
        try:
            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    return PlatformMetadata()
                
                data = await response.json()
                
                return PlatformMetadata(
                    bio=data.get("bio"),
                    display_name=data.get("name"),
                    location=data.get("location"),
                    website=data.get("blog"),
                    email=data.get("email"),
                    created_at=data.get("created_at"),
                    followers=data.get("followers"),
                    following=data.get("following"),
                    posts_count=data.get("public_repos"),
                    profile_image=data.get("avatar_url"),
                    custom_fields={
                        "company": data.get("company"),
                        "hireable": data.get("hireable"),
                        "twitter_username": data.get("twitter_username"),
                    },
                )
                
        except Exception:
            return PlatformMetadata()
    
    def validate_username(self, username: str) -> bool:
        """Validate GitHub username format."""
        if not username or len(username) > 39:
            return False
        
        # GitHub usernames: alphanumeric and hyphens, no consecutive hyphens
        # Cannot start or end with hyphen
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', username):
            return False
        
        if '--' in username:
            return False
        
        return True
