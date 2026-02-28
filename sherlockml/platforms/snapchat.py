"""Snapchat platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class SnapchatPlatform(HTTPCheckPlatform):
    """Snapchat profile checker via web."""

    name = "snapchat"
    display_name = "Snapchat"
    base_url = "https://snapchat.com"
    url_template = "https://snapchat.com/add/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) < 3 or len(username) > 15:
            return False
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9._-]+$', username))
