"""Wattpad platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class WattpadPlatform(HTTPCheckPlatform):
    """Wattpad writing/reading platform profile checker."""

    name = "wattpad"
    display_name = "Wattpad"
    base_url = "https://wattpad.com"
    url_template = "https://wattpad.com/user/{username}"
    category = PlatformCategory.CREATIVE
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
