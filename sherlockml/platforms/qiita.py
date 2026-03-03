"""Qiita platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class QiitaPlatform(HTTPCheckPlatform):
    """Qiita (qiita.com) developer blog checker."""

    name = "qiita"
    display_name = "Qiita"
    base_url = "https://qiita.com"
    url_template = "https://qiita.com/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 60.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"ページが見つかりません",
        r"ユーザーが見つかりません",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
