"""Naver Blog platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class NaverBlogPlatform(HTTPCheckPlatform):
    """Naver Blog (blog.naver.com) Korean blog checker."""

    name = "naver_blog"
    display_name = "Naver Blog"
    base_url = "https://blog.naver.com"
    url_template = "https://blog.naver.com/{username}"
    category = PlatformCategory.CREATIVE
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"페이지를 찾을 수 없습니다",
        r"사용자를 찾을 수 없습니다",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_]+$', username))
