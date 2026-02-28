"""DEV.to platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class DevToPlatform(HTTPCheckPlatform):
    """DEV.to developer blog checker."""

    name = "devto"
    display_name = "DEV.to"
    base_url = "https://dev.to"
    url_template = "https://dev.to/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
