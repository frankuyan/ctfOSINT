"""Gravatar platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class GravatarPlatform(HTTPCheckPlatform):
    """Gravatar profile checker - useful for linking email identities."""

    name = "gravatar"
    display_name = "Gravatar"
    base_url = "https://gravatar.com"
    url_template = "https://gravatar.com/{username}"
    category = PlatformCategory.OTHER
    rate_limit_rpm = 60.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
