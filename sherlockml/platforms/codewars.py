"""Codewars platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class CodewarsPlatform(HTTPCheckPlatform):
    """Codewars (codewars.com) coding challenge checker."""

    name = "codewars"
    display_name = "Codewars"
    base_url = "https://www.codewars.com"
    url_template = "https://www.codewars.com/users/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
