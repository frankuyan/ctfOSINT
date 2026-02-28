"""Linktree platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class LinktreePlatform(HTTPCheckPlatform):
    """Linktree profile checker - aggregates other platform links."""

    name = "linktree"
    display_name = "Linktree"
    base_url = "https://linktr.ee"
    url_template = "https://linktr.ee/{username}"
    category = PlatformCategory.OTHER
    rate_limit_rpm = 30.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 30:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
