"""Bandcamp platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class BandcampPlatform(HTTPCheckPlatform):
    """Bandcamp (bandcamp.com) music platform checker."""

    name = "bandcamp"
    display_name = "Bandcamp"
    base_url = "https://bandcamp.com"
    url_template = "https://{username}.bandcamp.com"
    category = PlatformCategory.MUSIC
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9-]+$', username))
