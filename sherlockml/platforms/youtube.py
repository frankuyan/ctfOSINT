"""YouTube platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class YouTubePlatform(HTTPCheckPlatform):
    """YouTube channel checker."""

    name = "youtube"
    display_name = "YouTube"
    base_url = "https://youtube.com"
    url_template = "https://youtube.com/@{username}"
    category = PlatformCategory.VIDEO
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9._-]+$', username))
