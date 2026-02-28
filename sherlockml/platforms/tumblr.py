"""Tumblr platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class TumblrPlatform(HTTPCheckPlatform):
    """Tumblr blog checker."""

    name = "tumblr"
    display_name = "Tumblr"
    base_url = "https://tumblr.com"
    url_template = "https://{username}.tumblr.com"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 32:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
