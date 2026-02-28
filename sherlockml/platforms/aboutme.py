"""About.me platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class AboutMePlatform(HTTPCheckPlatform):
    """About.me personal page checker."""

    name = "aboutme"
    display_name = "About.me"
    base_url = "https://about.me"
    url_template = "https://about.me/{username}"
    category = PlatformCategory.PROFESSIONAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
