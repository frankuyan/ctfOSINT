"""LinkedIn platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class LinkedInPlatform(HTTPCheckPlatform):
    """LinkedIn platform - limited due to heavy anti-scraping."""
    
    name = "linkedin"
    display_name = "LinkedIn"
    base_url = "https://linkedin.com"
    url_template = "https://linkedin.com/in/{username}"
    category = PlatformCategory.PROFESSIONAL
    rate_limit_rpm = 10.0  # Very conservative
    check_method = "GET"
    
    def validate_username(self, username: str) -> bool:
        """Validate LinkedIn vanity URL format."""
        if not username or len(username) < 3 or len(username) > 100:
            return False
        return bool(re.match(r'^[a-zA-Z0-9-]+$', username))
