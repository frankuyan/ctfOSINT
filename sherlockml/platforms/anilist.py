"""AniList platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class AniListPlatform(HTTPCheckPlatform):
    """AniList (anilist.co) anime/manga tracker checker."""

    name = "anilist"
    display_name = "AniList"
    base_url = "https://anilist.co"
    url_template = "https://anilist.co/user/{username}/"
    category = PlatformCategory.GAMING
    rate_limit_rpm = 60.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
