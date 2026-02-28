"""DeviantArt platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class DeviantArtPlatform(HTTPCheckPlatform):
    """DeviantArt profile checker."""

    name = "deviantart"
    display_name = "DeviantArt"
    base_url = "https://deviantart.com"
    url_template = "https://deviantart.com/{username}"
    category = PlatformCategory.CREATIVE
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
