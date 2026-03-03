"""Gitee platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class GiteePlatform(HTTPCheckPlatform):
    """Gitee (gitee.com) code hosting platform checker."""

    name = "gitee"
    display_name = "Gitee"
    base_url = "https://gitee.com"
    url_template = "https://gitee.com/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 40:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
