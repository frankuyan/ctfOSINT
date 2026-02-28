"""Tests for configuration loading and validation."""

import os
from pathlib import Path

import pytest

from sherlockml.config import (
    Config,
    CTFConfig,
    LoggingConfig,
    MLConfig,
    OutputConfig,
    PlatformConfig,
    ProxyConfig,
    SearchConfig,
    expand_env_vars,
    expand_path,
    load_config,
    save_config,
)


class TestExpandEnvVars:
    """Test environment variable expansion."""

    def test_expand_existing_var(self, monkeypatch):
        monkeypatch.setenv("TEST_TOKEN", "abc123")
        assert expand_env_vars("${TEST_TOKEN}") == "abc123"

    def test_expand_missing_var(self):
        assert expand_env_vars("${NONEXISTENT_VAR_XYZ}") == ""

    def test_no_expansion_needed(self):
        assert expand_env_vars("plain text") == "plain text"

    def test_mixed_expansion(self, monkeypatch):
        monkeypatch.setenv("USER_NAME", "alice")
        result = expand_env_vars("Hello ${USER_NAME}, welcome!")
        assert result == "Hello alice, welcome!"


class TestExpandPath:
    """Test path expansion."""

    def test_expand_tilde(self):
        result = expand_path("~/test")
        assert str(result).startswith(str(Path.home()))

    def test_expand_env_in_path(self, monkeypatch):
        monkeypatch.setenv("MY_DIR", "/opt/data")
        result = expand_path("${MY_DIR}/file.txt")
        assert str(result) == "/opt/data/file.txt"


class TestPlatformConfig:
    """Test platform configuration."""

    def test_defaults(self):
        pc = PlatformConfig()
        assert pc.enabled is True
        assert pc.priority_weight == 0.5
        assert pc.auth_token is None
        assert pc.instance_url is None

    def test_priority_weight_bounds(self):
        with pytest.raises(Exception):
            PlatformConfig(priority_weight=1.5)
        with pytest.raises(Exception):
            PlatformConfig(priority_weight=-0.1)

    def test_auth_token_env_expansion(self, monkeypatch):
        monkeypatch.setenv("GH_TOKEN", "ghp_secret123")
        pc = PlatformConfig(auth_token="${GH_TOKEN}")
        assert pc.auth_token == "ghp_secret123"


class TestMLConfig:
    """Test ML configuration."""

    def test_defaults(self):
        ml = MLConfig()
        assert ml.rag_threshold == 0.75
        assert ml.rl_learning_rate == 0.1
        assert ml.rl_exploration_rate == 0.15
        assert ml.vectorstore_type == "chromadb"
        assert ml.chromadb_host == "localhost"
        assert ml.chromadb_port == 8000
        assert ml.ner_model == "en_core_web_sm"
        assert ml.custom_patterns_file is None

    def test_path_properties(self):
        ml = MLConfig()
        assert isinstance(ml.ner_model_dir, Path)
        assert isinstance(ml.vectorstore_dir, Path)
        assert isinstance(ml.rl_weights_path, Path)


class TestSearchConfig:
    """Test search configuration."""

    def test_defaults(self):
        sc = SearchConfig()
        assert sc.max_concurrent == 25
        assert sc.request_timeout == 15.0
        assert sc.retry_attempts == 3
        assert len(sc.user_agents) >= 1


class TestProxyConfig:
    """Test proxy configuration."""

    def test_defaults(self):
        pc = ProxyConfig()
        assert pc.enabled is False
        assert pc.type == "socks5"
        assert pc.rotate_enabled is True
        assert pc.rotate_interval == 300
        assert pc.control_port == 9051

    def test_url_generation(self):
        pc = ProxyConfig(host="127.0.0.1", port=9050)
        assert pc.url == "socks5://127.0.0.1:9050"

    def test_url_with_auth(self):
        pc = ProxyConfig(host="proxy.example.com", port=1080, username="user", password="pass")
        assert "user:pass@" in pc.url


class TestOutputConfig:
    """Test output configuration."""

    def test_defaults(self):
        oc = OutputConfig()
        assert oc.default_format == "json"
        assert oc.results_dir == "~/.sherlockml/results"
        assert oc.graph_format == "svg"
        assert oc.graph_rankdir == "LR"


class TestCTFConfig:
    """Test CTF configuration."""

    def test_defaults(self):
        ctf = CTFConfig()
        assert ctf.auto_detect_format is True
        assert ctf.fast_fail is False
        assert len(ctf.flag_patterns) >= 2
        assert "github" in ctf.priority_platforms


class TestLoggingConfig:
    """Test logging configuration."""

    def test_defaults(self):
        lc = LoggingConfig()
        assert lc.level == "INFO"
        assert lc.file is None
        assert lc.rotate_size == 10_485_760
        assert lc.backup_count == 5


class TestConfig:
    """Test main Config model."""

    def test_defaults(self):
        config = Config()
        assert isinstance(config.ml, MLConfig)
        assert isinstance(config.search, SearchConfig)
        assert isinstance(config.proxy, ProxyConfig)
        assert isinstance(config.output, OutputConfig)
        assert isinstance(config.ctf, CTFConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_get_platform_existing(self):
        config = Config(platforms={"github": PlatformConfig(priority_weight=0.9)})
        pc = config.get_platform("github")
        assert pc.priority_weight == 0.9

    def test_get_platform_missing(self):
        config = Config()
        pc = config.get_platform("nonexistent")
        assert pc.enabled is True  # default
        assert pc.priority_weight == 0.5  # default


class TestLoadConfig:
    """Test config file loading."""

    def test_load_nonexistent_returns_defaults(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert isinstance(config, Config)

    def test_load_from_yaml(self, sample_config):
        config = load_config(sample_config)
        assert config.platforms["github"].enabled is True
        assert config.platforms["github"].priority_weight == 0.9
        assert config.ml.rag_threshold == 0.75

    def test_load_empty_file(self, tmp_path):
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        config = load_config(empty)
        assert isinstance(config, Config)


class TestSaveConfig:
    """Test config saving."""

    def test_save_and_reload(self, tmp_path):
        config = Config(
            platforms={"github": PlatformConfig(priority_weight=0.8)},
        )
        path = tmp_path / "config.yaml"
        save_config(config, path)

        assert path.exists()
        reloaded = load_config(path)
        assert reloaded.platforms["github"].priority_weight == 0.8
