"""Letterboxd platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class LetterboxdPlatform(HTTPCheckPlatform):
    """Letterboxd profile checker."""

    name = "letterboxd"
    display_name = "Letterboxd"
    base_url = "https://letterboxd.com"
    url_template = "https://letterboxd.com/{username}/"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 15.0
    check_method = "GET"

    # Letterboxd returns 404 for non-existent users
    not_found_status_codes = {404}
    
    def validate_username(self, username: str) -> bool:
        """Validate Letterboxd username format."""
        if not username or len(username) < 2 or len(username) > 15:
            return False
        # Letterboxd usernames are typically alphanumeric plus underscores/dashes
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
