"""VKontakte platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class VKPlatform(HTTPCheckPlatform):
    """VKontakte (vk.com) social network checker."""

    name = "vk"
    display_name = "VKontakte"
    base_url = "https://vk.com"
    url_template = "https://vk.com/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"Страница не найдена",
        r"Пользователь не найден",
        r"(?i)page\s+not\s+available",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 32:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
