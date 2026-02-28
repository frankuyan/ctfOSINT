"""Dailymotion platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class DailymotionPlatform(HTTPCheckPlatform):
    """Dailymotion video platform profile checker."""

    name = "dailymotion"
    display_name = "Dailymotion"
    base_url = "https://dailymotion.com"
    url_template = "https://dailymotion.com/{username}"
    category = PlatformCategory.VIDEO
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 25:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
