"""MyAnimeList platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class MyAnimeListPlatform(HTTPCheckPlatform):
    """MyAnimeList (myanimelist.net) anime tracker checker."""

    name = "myanimelist"
    display_name = "MyAnimeList"
    base_url = "https://myanimelist.net"
    url_template = "https://myanimelist.net/profile/{username}"
    category = PlatformCategory.GAMING
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) < 2 or len(username) > 16:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
