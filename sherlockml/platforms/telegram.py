"""Telegram platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class TelegramPlatform(HTTPCheckPlatform):
    """Telegram public profile checker."""

    name = "telegram"
    display_name = "Telegram"
    base_url = "https://t.me"
    url_template = "https://t.me/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) < 5 or len(username) > 32:
            return False
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]+$', username))
