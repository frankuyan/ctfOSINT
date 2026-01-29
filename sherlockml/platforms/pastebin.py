"""Pastebin platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class PastebinPlatform(HTTPCheckPlatform):
    """Pastebin platform - high CTF relevance for flag leaks."""
    
    name = "pastebin"
    display_name = "Pastebin"
    base_url = "https://pastebin.com"
    url_template = "https://pastebin.com/u/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 30.0
    check_method = "GET"
    
    def validate_username(self, username: str) -> bool:
        """Validate Pastebin username format."""
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
