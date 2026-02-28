"""Spotify platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class SpotifyPlatform(HTTPCheckPlatform):
    """Spotify user profile checker."""

    name = "spotify"
    display_name = "Spotify"
    base_url = "https://open.spotify.com"
    url_template = "https://open.spotify.com/user/{username}"
    category = PlatformCategory.MUSIC
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9._-]+$', username))
