"""Tests for proxy-aware session creation.

Every target-facing request must honour the configured proxy; these tests
pin that for the shared factory and for each CLI command that opens a
session outside the orchestrator.
"""

from unittest.mock import patch

import pytest
from aiohttp_socks import ProxyConnector
from click.testing import CliRunner

from sherlockml.cli import main
from sherlockml.config import Config, ProxyConfig
from sherlockml.enum.orchestrator import Orchestrator
from sherlockml.net import apply_proxy_option, create_session


class TestCreateSession:
    async def test_direct_when_proxy_disabled(self):
        async with create_session(Config()) as session:
            assert not isinstance(session.connector, ProxyConnector)

    async def test_proxied_when_enabled(self):
        config = Config()
        apply_proxy_option(config, "socks5://127.0.0.1:9050")
        async with create_session(config, timeout=5) as session:
            assert isinstance(session.connector, ProxyConnector)
            assert session.timeout.total == 5

    async def test_orchestrator_uses_proxy(self):
        config = Config()
        apply_proxy_option(config, "socks5://127.0.0.1:9050")
        async with await Orchestrator(config)._create_session() as session:
            assert isinstance(session.connector, ProxyConnector)


class TestProxyOption:
    def test_parses_full_url(self):
        config = Config()
        apply_proxy_option(config, "http://user:pw@proxy.local:8080")
        assert config.proxy.enabled
        assert config.proxy.url == "http://user:pw@proxy.local:8080"

    @pytest.mark.parametrize("scheme", ["tor", "socks5h"])
    def test_tor_and_socks5h_map_to_socks5(self, scheme):
        proxy = ProxyConfig(enabled=True, type=scheme, host="127.0.0.1", port=9050)
        assert proxy.url == "socks5://127.0.0.1:9050"


class _SessionSpy(Exception):
    """Raised by the patched factory to stop the command once we've seen the config."""


def _spy(seen):
    def fake_create_session(config, **kwargs):
        seen.append(config.proxy.url if config.proxy.enabled else None)
        raise _SessionSpy
    return fake_create_session


class TestCommandsHonourProxy:
    @pytest.mark.parametrize("argv", [
        ["wayback", "https://example.com", "--proxy", "socks5://127.0.0.1:9050"],
        ["scan-github", "someone", "--proxy", "socks5://127.0.0.1:9050"],
    ])
    def test_command_routes_through_proxy(self, argv):
        seen: list[str | None] = []
        with patch("sherlockml.cli.load_config", return_value=Config()), \
             patch("sherlockml.cli.create_session", side_effect=_spy(seen)):
            result = CliRunner().invoke(main, argv)
        assert isinstance(result.exception, _SessionSpy)
        assert seen == ["socks5://127.0.0.1:9050"]

    def test_config_proxy_used_without_flag(self):
        config = Config()
        config.proxy.enabled = True
        seen: list[str | None] = []
        with patch("sherlockml.cli.load_config", return_value=config), \
             patch("sherlockml.cli.create_session", side_effect=_spy(seen)):
            CliRunner().invoke(main, ["wayback", "https://example.com"])
        assert seen == ["socks5://127.0.0.1:9050"]
