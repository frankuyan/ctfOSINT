"""Fiverr platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class FiverrPlatform(HTTPCheckPlatform):
    """Fiverr (fiverr.com) freelance marketplace checker."""

    name = "fiverr"
    display_name = "Fiverr"
    base_url = "https://www.fiverr.com"
    url_template = "https://www.fiverr.com/{username}"
    category = PlatformCategory.PROFESSIONAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
