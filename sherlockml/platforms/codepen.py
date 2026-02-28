"""CodePen platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class CodePenPlatform(HTTPCheckPlatform):
    """CodePen front-end developer profile checker."""

    name = "codepen"
    display_name = "CodePen"
    base_url = "https://codepen.io"
    url_template = "https://codepen.io/{username}"
    category = PlatformCategory.CODE
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
