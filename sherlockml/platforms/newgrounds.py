"""Newgrounds platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class NewgroundsPlatform(HTTPCheckPlatform):
    """Newgrounds creative community profile checker."""

    name = "newgrounds"
    display_name = "Newgrounds"
    base_url = "https://newgrounds.com"
    url_template = "https://{username}.newgrounds.com"
    category = PlatformCategory.CREATIVE
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
