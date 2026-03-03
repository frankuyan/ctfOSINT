"""Pikabu platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class PikabuPlatform(HTTPCheckPlatform):
    """Pikabu (pikabu.ru) social/forum checker."""

    name = "pikabu"
    display_name = "Pikabu"
    base_url = "https://pikabu.ru"
    url_template = "https://pikabu.ru/@{username}"
    category = PlatformCategory.FORUM
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"Страница не найдена",
        r"не существует",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
