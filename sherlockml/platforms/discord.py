"""Discord platform module - checks via Discord lookup services."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class DiscordPlatform(HTTPCheckPlatform):
    """Discord profile lookup via discordlookup.com."""

    name = "discord"
    display_name = "Discord"
    base_url = "https://discord.com"
    url_template = "https://discord.com/users/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 15.0
    check_method = "GET"

    def validate_username(self, username: str) -> bool:
        if not username or len(username) < 2 or len(username) > 32:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.]+$', username))
