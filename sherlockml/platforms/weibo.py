"""Weibo platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class WeiboPlatform(HTTPCheckPlatform):
    """Weibo (weibo.com) social media checker."""

    name = "weibo"
    display_name = "Weibo"
    base_url = "https://weibo.com"
    url_template = "https://weibo.com/n/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"该用户不存在",
        r"用户不存在",
        r"(?i)user\s+does\s+not\s+exist",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[\w\u4e00-\u9fff]+$', username))
