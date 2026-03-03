"""Baidu Tieba platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class BaiduTiebaPlatform(HTTPCheckPlatform):
    """Baidu Tieba (tieba.baidu.com) forum checker."""

    name = "baidu_tieba"
    display_name = "Baidu Tieba"
    base_url = "https://tieba.baidu.com"
    url_template = "https://tieba.baidu.com/home/main?un={username}"
    category = PlatformCategory.FORUM
    rate_limit_rpm = 20.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"该用户不存在",
        r"用户不存在",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[\w\u4e00-\u9fff]+$', username))
