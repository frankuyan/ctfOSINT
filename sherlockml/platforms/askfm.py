"""ASKfm platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class AskFmPlatform(HTTPCheckPlatform):
    """ASKfm Q&A social profile checker."""

    name = "askfm"
    display_name = "ASKfm"
    base_url = "https://ask.fm"
    url_template = "https://ask.fm/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 20:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
