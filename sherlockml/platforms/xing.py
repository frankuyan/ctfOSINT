"""XING platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class XingPlatform(HTTPCheckPlatform):
    """XING (xing.com) professional network checker."""

    name = "xing"
    display_name = "XING"
    base_url = "https://www.xing.com"
    url_template = "https://www.xing.com/profile/{username}"
    category = PlatformCategory.PROFESSIONAL
    rate_limit_rpm = 30.0
    check_method = "GET"

    not_found_text_patterns = [
        *HTTPCheckPlatform.not_found_text_patterns,
        r"(?i)seite\s+nicht\s+gefunden",
        r"(?i)benutzer\s+nicht\s+gefunden",
    ]

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 50:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.-]+$', username))
