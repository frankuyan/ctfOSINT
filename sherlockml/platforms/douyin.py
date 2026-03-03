"""Douyin platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class DouyinPlatform(HTTPCheckPlatform):
    """Douyin / TikTok China (douyin.com) video platform checker."""

    name = "douyin"
    display_name = "Douyin"
    base_url = "https://www.douyin.com"
    url_template = "https://www.douyin.com/user/{username}"
    category = PlatformCategory.VIDEO
    rate_limit_rpm = 20.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"该用户不存在",
        r"页面未找到",
        r"此页面不存在",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 50:
            return False
        return bool(re.match(r'^[\w]+$', username))
