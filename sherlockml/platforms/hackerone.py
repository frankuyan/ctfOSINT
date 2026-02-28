"""HackerOne platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class HackerOnePlatform(HTTPCheckPlatform):
    """HackerOne bug bounty profile checker."""

    name = "hackerone"
    display_name = "HackerOne"
    base_url = "https://hackerone.com"
    url_template = "https://hackerone.com/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
