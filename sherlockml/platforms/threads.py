"""Threads (Meta) platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class ThreadsPlatform(HTTPCheckPlatform):
    """Threads (Meta) social profile checker."""

    name = "threads"
    display_name = "Threads"
    base_url = "https://threads.net"
    url_template = "https://threads.net/@{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
