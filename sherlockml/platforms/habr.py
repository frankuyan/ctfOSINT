"""Habr platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class HabrPlatform(HTTPCheckPlatform):
    """Habr (habr.com) developer blog/news checker."""

    name = "habr"
    display_name = "Habr"
    base_url = "https://habr.com"
    url_template = "https://habr.com/ru/users/{username}/"
    category = PlatformCategory.CODE
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"Страница не найдена",
        r"Пользователь не найден",
        r"не существует",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
