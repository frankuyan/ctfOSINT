"""Mastodon platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class MastodonPlatform(HTTPCheckPlatform):
    """Mastodon platform - checks mastodon.social by default."""
    
    name = "mastodon"
    display_name = "Mastodon"
    base_url = "https://mastodon.social"
    url_template = "https://mastodon.social/@{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 60.0
    check_method = "GET"
    
    def validate_username(self, username: str) -> bool:
        """Validate Mastodon username format."""
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
