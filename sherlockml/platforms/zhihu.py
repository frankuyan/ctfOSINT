"""Zhihu platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class ZhihuPlatform(HTTPCheckPlatform):
    """Zhihu (zhihu.com) Q&A platform checker."""

    name = "zhihu"
    display_name = "Zhihu"
    base_url = "https://www.zhihu.com"
    url_template = "https://www.zhihu.com/people/{username}"
    category = PlatformCategory.FORUM
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"该用户不存在",
        r"页面未找到",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 50:
            return False
        return bool(re.match(r'^[\w-]+$', username))
