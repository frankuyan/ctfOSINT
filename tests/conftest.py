"""Pytest configuration and fixtures for SherlockML tests."""

from pathlib import Path
from typing import Generator

import pytest

from sherlockml.enum.platform_base import BasePlatform, PlatformResult


class StubPlatform(BasePlatform):
    """Offline platform for orchestrator tests.

    ``pages`` maps username -> raw HTML for accounts that exist; any other
    username is reported as not found.  With ``pages=None`` every username
    exists.  ``bio`` is returned as metadata on every hit.
    """

    name = "stub"
    display_name = "Stub"
    base_url = "https://stub.example"
    url_template = "https://stub.example/{username}"
    rate_limit_rpm = 6000.0

    def __init__(self, pages=None, bio="", name=None, metadata=None):
        super().__init__()
        self.pages = pages
        self.bio = bio
        self.extra_metadata = metadata or {}
        if name:
            self.name = name
            self.url_template = f"https://{name}.example/{{username}}"

    async def check_username(self, username, session):
        if self.pages is not None and username not in self.pages:
            return PlatformResult(exists=False, confidence=0.95)
        raw = self.pages.get(username) if self.pages is not None else None
        return PlatformResult(
            exists=True,
            url=self.get_url(username),
            metadata={"bio": self.bio, **self.extra_metadata},
            confidence=0.9,
            raw_response=raw,
        )


@pytest.fixture
def stub_platform():
    """Factory for offline StubPlatform instances."""
    return StubPlatform


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary config directory."""
    config_dir = tmp_path / ".sherlockml"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config(temp_config_dir: Path) -> Path:
    """Create a sample config file."""
    config_content = """
platforms:
  github:
    enabled: true
    priority_weight: 0.9
  twitter:
    enabled: true
    priority_weight: 0.7

ml:
  rag_threshold: 0.75
  rl_learning_rate: 0.1

search:
  max_concurrent: 5
  request_timeout: 10
"""
    config_path = temp_config_dir / "config.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_html() -> str:
    """Sample HTML for parsing tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="me" href="https://github.com/testuser">
        <meta property="og:title" content="Test User">
    </head>
    <body>
        <a href="https://twitter.com/testuser" rel="me">Twitter</a>
        <a href="https://linkedin.com/in/testuser">LinkedIn</a>
        <p>Contact: test@example.com</p>
        <p>Found a flag{test_flag_123} in the code!</p>
    </body>
    </html>
    """


@pytest.fixture
def sample_ctf_text() -> str:
    """Sample text with CTF-related content."""
    return """
    Looking for flags in this challenge!
    Found: flag{s3cr3t_fl4g_h3r3}
    Also found CTF{another_one}
    
    Email: user@ctfchallenge.com
    Hash: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
    
    Check out my GitHub: github.com/ctfplayer
    And Twitter: @ctf_player_1337
    """


@pytest.fixture
def mock_github_response() -> dict:
    """Mock GitHub API response."""
    return {
        "login": "testuser",
        "name": "Test User",
        "bio": "CTF player and security researcher",
        "location": "San Francisco",
        "email": None,
        "html_url": "https://github.com/testuser",
        "public_repos": 42,
        "followers": 100,
        "following": 50,
        "created_at": "2020-01-01T00:00:00Z",
    }
