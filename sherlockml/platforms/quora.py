"""Quora platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class QuoraPlatform(HTTPCheckPlatform):
    """Quora Q&A profile checker."""

    name = "quora"
    display_name = "Quora"
    base_url = "https://quora.com"
    url_template = "https://quora.com/profile/{username}"
    category = PlatformCategory.FORUM
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 50:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
