"""TryHackMe platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class TryHackMePlatform(HTTPCheckPlatform):
    """TryHackMe CTF platform profile checker."""

    name = "tryhackme"
    display_name = "TryHackMe"
    base_url = "https://tryhackme.com"
    url_template = "https://tryhackme.com/p/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
