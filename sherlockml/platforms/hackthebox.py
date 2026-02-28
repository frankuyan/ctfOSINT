"""Hack The Box platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class HackTheBoxPlatform(HTTPCheckPlatform):
    """Hack The Box CTF platform profile checker."""

    name = "hackthebox"
    display_name = "Hack The Box"
    base_url = "https://app.hackthebox.com"
    url_template = "https://app.hackthebox.com/users/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
