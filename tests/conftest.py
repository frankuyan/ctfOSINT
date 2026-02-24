"""Pytest configuration and fixtures for SherlockML tests."""

from pathlib import Path
from typing import Generator

import pytest


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
