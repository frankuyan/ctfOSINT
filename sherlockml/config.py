"""Configuration system for SherlockML."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from sherlockml.flags import DEFAULT_FLAG_PATTERNS


def expand_env_vars(value: str) -> str:
    """Expand ${VAR} environment variables in string values.

    Missing variables are replaced with empty string, but a warning is
    logged so callers can detect misconfiguration.
    """
    import logging

    _env_pattern = re.compile(r'\$\{([^}]+)\}')

    def replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is None:
            logging.getLogger(__name__).warning(
                "Environment variable %s is not set (referenced in config value)",
                var_name,
            )
            return ''
        return env_value

    return _env_pattern.sub(replacer, value)


def expand_path(path: str) -> Path:
    """Expand ~ and environment variables in paths."""
    return Path(os.path.expanduser(expand_env_vars(path)))


class PlatformConfig(BaseModel):
    """Configuration for a single platform."""
    enabled: bool = True
    priority_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    auth_token: str | None = None
    search_commits: bool = False
    custom_headers: dict[str, str] = Field(default_factory=dict)
    rate_limit: float | None = None  # Platform-specific rate limit override
    instance_url: str | None = None  # For federated platforms (e.g. Mastodon)
    
    @field_validator('auth_token', mode='before')
    @classmethod
    def expand_auth_token(cls, v: str | None) -> str | None:
        if v is not None:
            return expand_env_vars(v)
        return v


class MLConfig(BaseModel):
    """Machine learning configuration."""
    rag_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    rl_learning_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    rl_exploration_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    ner_model_path: str = "~/.sherlockml/ner_model"
    ner_model: str = "en_core_web_sm"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vectorstore_type: str = "chromadb"  # chromadb or qdrant
    vectorstore_path: str = "~/.sherlockml/vectorstore"
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    rl_weights_db: str = "~/.sherlockml/rl_weights.db"
    custom_patterns_file: str | None = None
    
    @property
    def ner_model_dir(self) -> Path:
        return expand_path(self.ner_model_path)
    
    @property
    def vectorstore_dir(self) -> Path:
        return expand_path(self.vectorstore_path)
    
    @property
    def rl_weights_path(self) -> Path:
        return expand_path(self.rl_weights_db)


class SearchConfig(BaseModel):
    """Search behavior configuration."""
    max_concurrent: int = Field(default=25, ge=1, le=100)
    request_timeout: float = Field(default=15.0, ge=1.0, le=120.0)
    user_agents: list[str] = Field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ])
    default_rate_limit: float = Field(default=5.0, ge=0.1, le=100.0)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, ge=0.0, le=30.0)


class ProxyConfig(BaseModel):
    """Proxy configuration."""
    enabled: bool = False
    type: str = "socks5"  # socks5, http, tor
    host: str = "127.0.0.1"
    port: int = 9050
    username: str | None = None
    password: str | None = None
    rotate: bool = False  # Rotate through proxy list
    rotate_enabled: bool = True  # Enable identity rotation
    rotate_interval: int = 300  # Seconds between rotations
    control_port: int = 9051  # Tor control port
    
    @property
    def url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        # Tor is a SOCKS5 proxy; socks5h is curl's spelling of SOCKS5 with
        # remote DNS, which aiohttp-socks already does for socks5.
        scheme = "socks5" if self.type in ("tor", "socks5h") else self.type
        return f"{scheme}://{auth}{self.host}:{self.port}"


class OutputConfig(BaseModel):
    """Output configuration."""
    default_format: str = "json"  # json, markdown, graphviz
    include_raw_responses: bool = False
    pretty_print: bool = True
    flags_file: str = "~/.sherlockml/flags.json"
    results_dir: str = "~/.sherlockml/results"
    writeup_template: str = "~/.sherlockml/templates/writeup.md.j2"
    graph_format: str = "svg"
    graph_rankdir: str = "LR"
    
    @property
    def flags_path(self) -> Path:
        return expand_path(self.flags_file)


class CTFConfig(BaseModel):
    """CTF-specific optimizations."""
    auto_detect_format: bool = True
    flag_patterns: list[str] = Field(default_factory=lambda: list(DEFAULT_FLAG_PATTERNS))
    fast_fail: bool = False  # Stop after first flag found
    time_travel_date: str | None = None  # Set search date for historical queries
    priority_platforms: list[str] = Field(default_factory=lambda: [
        "reddit", "twitter", "mastodon", "bluesky",
        "pastebin", "github", "gist", "keybase", "hackernews",
        "tryhackme", "hackthebox", "hackerone", "gitlab", "bitbucket", "gitea",
    ])


class LLMConfig(BaseModel):
    """LLM configuration for profile verification."""
    enabled: bool = False
    provider: str = "openai"  # openai, anthropic, gemini, or openai-compatible
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    base_url: str | None = None  # For openai-compatible endpoints
    max_tokens: int = 256
    max_concurrent_verifications: int = 5
    verify_found_only: bool = True  # Only verify profiles marked as found

    @field_validator('api_key', mode='before')
    @classmethod
    def expand_api_key(cls, v: str | None) -> str | None:
        if v is not None:
            return expand_env_vars(v)
        return v

    @field_validator('base_url', mode='before')
    @classmethod
    def expand_base_url(cls, v: str | None) -> str | None:
        if v is not None:
            return expand_env_vars(v)
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = None
    rotate_size: int = 10_485_760  # 10MB
    backup_count: int = 5


class Config(BaseModel):
    """Main SherlockML configuration."""
    platforms: dict[str, PlatformConfig] = Field(default_factory=dict)
    ml: MLConfig = Field(default_factory=MLConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    ctf: CTFConfig = Field(default_factory=CTFConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    plugins_dir: str = "~/.sherlockml/plugins"
    data_dir: str = "~/.sherlockml/data"
    
    @property
    def plugins_path(self) -> Path:
        return expand_path(self.plugins_dir)
    
    @property
    def data_path(self) -> Path:
        return expand_path(self.data_dir)
    
    def get_platform(self, name: str) -> PlatformConfig:
        """Get platform config, returning defaults if not configured."""
        return self.platforms.get(name, PlatformConfig())


def load_config(config_path: Path | str | None = None) -> Config:
    """Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. Defaults to ~/.sherlockml/config.yaml
        
    Returns:
        Loaded Config object
    """
    if config_path is None:
        # Check environment variable first
        env_config = os.environ.get('SHERLOCKML_CONFIG')
        if env_config:
            path = Path(env_config)
            config_path = path / 'config.yaml' if path.is_dir() else path
        else:
            config_path = Path.home() / '.sherlockml' / 'config.yaml'
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        # Return default config if file doesn't exist
        return Config()
    
    with open(config_path) as f:
        raw_config = yaml.safe_load(f)
    
    if raw_config is None:
        return Config()
    
    return Config.model_validate(raw_config)


def save_config(config: Config, config_path: Path | str | None = None) -> None:
    """Save configuration to YAML file.
    
    Args:
        config: Config object to save
        config_path: Path to save to. Defaults to ~/.sherlockml/config.yaml
    """
    if config_path is None:
        config_path = Path.home() / '.sherlockml' / 'config.yaml'
    else:
        config_path = Path(config_path)
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        yaml.dump(config.model_dump(exclude_none=True), f, default_flow_style=False)


def create_default_config_file(config_path: Path | str | None = None) -> Path:
    """Create a default config file with example values.
    
    Args:
        config_path: Path for config file. Defaults to ~/.sherlockml/config.yaml
        
    Returns:
        Path to created config file
    """
    if config_path is None:
        config_path = Path.home() / '.sherlockml' / 'config.yaml'
    else:
        config_path = Path(config_path)
    
    default_content = """\
# SherlockML Configuration
# See documentation for full options

platforms:
  github:
    enabled: true
    priority_weight: 0.92
    auth_token: ${GITHUB_TOKEN}
    search_commits: true
  twitter:
    enabled: true
    priority_weight: 0.88
  linkedin:
    enabled: true
    priority_weight: 0.65
  reddit:
    enabled: true
    priority_weight: 0.90
  mastodon:
    enabled: true
    priority_weight: 0.85
  hackernews:
    enabled: true
    priority_weight: 0.80
  pastebin:
    enabled: true
    priority_weight: 0.85

ml:
  rag_threshold: 0.75
  rl_learning_rate: 0.1
  ner_model_path: ~/.sherlockml/ner_model
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  vectorstore_path: ~/.sherlockml/vectorstore
  rl_weights_db: ~/.sherlockml/rl_weights.db

search:
  max_concurrent: 25
  request_timeout: 15
  default_rate_limit: 5.0
  retry_attempts: 3
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0"

proxy:
  enabled: false
  type: socks5
  host: 127.0.0.1
  port: 9050

output:
  default_format: json
  pretty_print: true

llm:
  enabled: false
  provider: openai          # openai, anthropic, gemini, or openai-compatible
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini
  # base_url: http://localhost:11434/v1  # For local models (Ollama, etc.)
  max_tokens: 256
  max_concurrent_verifications: 5

ctf:
  auto_detect_format: true
  fast_fail: false
  flag_patterns:
    - '(flag|ctf|glug|hxp|picoCTF|HTB)\\{[^}]+\\}'
"""
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(default_content)
    
    return config_path
