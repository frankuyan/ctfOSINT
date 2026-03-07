"""VSCO platform module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sherlockml.enum.platform_base import (
    HTTPCheckPlatform,
    PlatformCategory,
)

if TYPE_CHECKING:
    import aiohttp


class VSCOPlatform(HTTPCheckPlatform):
    """VSCO profile checker."""

    name = "vsco"
    display_name = "VSCO"
    base_url = "https://vsco.co"
    url_template = "https://vsco.co/{username}"
    category = PlatformCategory.SOCIAL
    rate_limit_rpm = 15.0
    check_method = "GET"

    # VSCO often returns 403 for automated requests, but let's try standard 404
    not_found_status_codes = {404}
    
    def validate_username(self, username: str) -> bool:
        """Validate VSCO username format."""
        if not username or len(username) < 3 or len(username) > 30:
            return False
        # VSCO usernames are typically alphanumeric plus underscores/dashes
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))
