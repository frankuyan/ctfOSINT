"""Xbox Gamertag platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class XboxGamertagPlatform(HTTPCheckPlatform):
    """Xbox Live gamertag profile checker."""

    name = "xbox"
    display_name = "Xbox Live"
    base_url = "https://account.xbox.com"
    url_template = "https://account.xbox.com/en-us/profile?gamertag={username}"
    category = PlatformCategory.GAMING
    rate_limit_rpm = 20.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) > 15:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_ ]+$', username))
