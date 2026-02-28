"""TikTok platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class TikTokPlatform(HTTPCheckPlatform):
    """TikTok profile checker."""

    name = "tiktok"
    display_name = "TikTok"
    base_url = "https://tiktok.com"
    url_template = "https://tiktok.com/@{username}"
    category = PlatformCategory.VIDEO
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 24:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
