"""HTTP session factory shared by every command that contacts a target.

Anything that sends a request to a platform, an archive or a profile page
must go through :func:`create_session` so the configured proxy (e.g. Tor)
is honoured.  A session built with plain ``aiohttp.ClientSession()`` would
connect directly and expose the investigator's IP address.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

import aiohttp
from aiohttp_socks import ProxyConnector

if TYPE_CHECKING:
    from sherlockml.config import Config


def create_session(
    config: "Config",
    *,
    timeout: float | None = None,
    headers: dict[str, str] | None = None,
) -> aiohttp.ClientSession:
    """Build an aiohttp session that routes through ``config.proxy`` if enabled.

    Args:
        config: Application configuration
        timeout: Total request timeout in seconds (default: search.request_timeout)
        headers: Default headers for every request
    """
    connector = ProxyConnector.from_url(config.proxy.url) if config.proxy.enabled else None
    return aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=timeout or config.search.request_timeout),
        headers=headers,
    )


def apply_proxy_option(config: "Config", proxy: str) -> None:
    """Enable the proxy described by a ``scheme://[user:pass@]host:port`` URL."""
    parsed = urlparse(proxy)
    config.proxy.enabled = True
    if parsed.scheme:
        config.proxy.type = parsed.scheme
    if parsed.hostname:
        config.proxy.host = parsed.hostname
    if parsed.port:
        config.proxy.port = parsed.port
    if parsed.username:
        config.proxy.username = parsed.username
    if parsed.password:
        config.proxy.password = parsed.password
