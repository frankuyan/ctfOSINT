"""Vimeo platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class VimeoPlatform(HTTPCheckPlatform):
    """Vimeo user profile checker."""

    name = "vimeo"
    display_name = "Vimeo"
    base_url = "https://vimeo.com"
    url_template = "https://vimeo.com/{username}"
    category = PlatformCategory.VIDEO
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
