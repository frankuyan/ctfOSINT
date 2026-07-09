"""Tests for per-platform custom header wiring."""

import pytest

from sherlockml.config import Config, PlatformConfig
from sherlockml.enum.platform_base import (
    DEFAULT_USER_AGENT,
    BasePlatform,
    PlatformResult,
)
from sherlockml.enum.registry import PlatformRegistry


class _DummyPlatform(BasePlatform):
    name = "dummy"
    display_name = "Dummy"
    base_url = "https://dummy.test"
    url_template = "https://dummy.test/{username}"

    async def check_username(self, username, session) -> PlatformResult:  # pragma: no cover
        return PlatformResult(exists=False)


class TestGetHeaders:
    def test_defaults_without_custom_headers(self):
        p = _DummyPlatform()
        headers = p.get_headers()
        assert headers["User-Agent"] == DEFAULT_USER_AGENT
        assert "Accept" in headers

    def test_custom_headers_added(self):
        p = _DummyPlatform(custom_headers={"X-Api-Key": "secret"})
        assert p.get_headers()["X-Api-Key"] == "secret"

    def test_custom_headers_override_defaults(self):
        p = _DummyPlatform(custom_headers={"User-Agent": "CustomUA/1.0"})
        assert p.get_headers()["User-Agent"] == "CustomUA/1.0"

    def test_custom_headers_default_empty(self):
        assert _DummyPlatform().custom_headers == {}


class TestRegistryThreadsHeaders:
    @pytest.fixture
    def registry(self):
        reg = PlatformRegistry(plugins_dir=None)
        reg.register(_DummyPlatform)
        return reg

    def test_get_passes_custom_headers(self, registry):
        p = registry.get("dummy", custom_headers={"X-Test": "1"})
        assert p is not None
        assert p.get_headers()["X-Test"] == "1"

    def test_cache_disambiguates_by_headers(self, registry):
        a = registry.get("dummy", custom_headers={"X-Test": "1"})
        b = registry.get("dummy", custom_headers={"X-Test": "2"})
        same = registry.get("dummy", custom_headers={"X-Test": "1"})
        assert a is not b  # different header sets -> different instances
        assert a is same  # identical params -> cached

    def test_get_enabled_applies_config_headers(self, registry):
        config = Config(
            platforms={
                "dummy": PlatformConfig(
                    enabled=True, custom_headers={"X-From-Config": "yes"}
                )
            }
        )
        enabled = registry.get_enabled(config)
        assert enabled
        assert enabled[0].get_headers()["X-From-Config"] == "yes"
