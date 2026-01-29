# Configuration Guide

SherlockML uses YAML configuration files for flexible customization.

## Configuration File Location

Default location: `~/.sherlockml/config.yaml`

Override with:
```bash
sherlockml --config /path/to/config.yaml search username
```

Or set environment variable:
```bash
export SHERLOCKML_CONFIG=/path/to/config.yaml
```

## Configuration Structure

```yaml
# Full configuration example
platforms: {}      # Platform-specific settings
ml: {}             # Machine learning settings
search: {}         # Search behavior settings
proxy: {}          # Proxy configuration
output: {}         # Output format settings
ctf: {}            # CTF-specific settings
logging: {}        # Logging configuration
```

---

## Platform Configuration

### Global Platform Settings

```yaml
platforms:
  github:
    enabled: true              # Enable/disable platform
    priority_weight: 0.92      # RL priority (0.0-1.0)
    auth_token: ${GITHUB_TOKEN}  # API token (env var expansion)
    rate_limit: 30.0           # Requests per minute
    timeout: 15                # Request timeout in seconds
```

### Per-Platform Options

#### GitHub

```yaml
platforms:
  github:
    enabled: true
    priority_weight: 0.92
    auth_token: ${GITHUB_TOKEN}
    rate_limit: 30.0
    search_commits: true       # Enable commit searching
    search_gists: true         # Enable gist searching
```

#### Twitter/X

```yaml
platforms:
  twitter:
    enabled: true
    priority_weight: 0.78
    auth_token: ${TWITTER_BEARER_TOKEN}
    rate_limit: 5.0
```

#### Mastodon

```yaml
platforms:
  mastodon:
    enabled: true
    priority_weight: 0.55
    instance_url: https://mastodon.social  # Instance to check
    rate_limit: 10.0
```

#### LinkedIn

```yaml
platforms:
  linkedin:
    enabled: true
    priority_weight: 0.65
    rate_limit: 2.0            # Conservative rate limit
```

### All Built-in Platforms

| Platform | Default Weight | Rate Limit | Auth Required |
|----------|---------------|------------|---------------|
| github | 0.92 | 30/min | Optional |
| gitlab | 0.85 | 20/min | Optional |
| twitter | 0.78 | 5/min | Optional |
| reddit | 0.70 | 10/min | No |
| linkedin | 0.65 | 2/min | No |
| instagram | 0.60 | 3/min | No |
| mastodon | 0.55 | 10/min | No |
| hackernews | 0.80 | 10/min | No |
| keybase | 0.88 | 10/min | No |
| pastebin | 0.85 | 5/min | No |

---

## Machine Learning Configuration

```yaml
ml:
  # RAG (Retrieval-Augmented Generation) Settings
  rag_threshold: 0.75          # Minimum similarity score for results
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  vectorstore_type: chromadb   # chromadb or qdrant
  vectorstore_path: ~/.sherlockml/vectorstore
  
  # For ChromaDB server mode
  chromadb_host: localhost
  chromadb_port: 8000
  
  # For Qdrant
  qdrant_host: localhost
  qdrant_port: 6333
  qdrant_collection: sherlockml
  
  # RL (Reinforcement Learning) Settings
  rl_learning_rate: 0.1        # Learning rate for updates
  rl_weights_db: ~/.sherlockml/rl_weights.db
  rl_exploration_rate: 0.15    # Thompson sampling exploration
  
  # NER (Named Entity Recognition) Settings
  ner_model: en_core_web_sm    # SpaCy model name
  custom_patterns_file: ~/.sherlockml/ner_patterns.yaml
```

---

## Search Configuration

```yaml
search:
  max_concurrent: 10           # Max parallel requests
  request_timeout: 15          # Seconds per request
  default_rate_limit: 5.0      # Global requests/second
  retry_attempts: 3            # Retry failed requests
  retry_backoff: 1.5           # Exponential backoff multiplier
  
  # User agent rotation
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36"
    - "SherlockML/1.0 (OSINT Research Tool)"
```

---

## Proxy Configuration

```yaml
proxy:
  enabled: false
  type: socks5                 # socks5, socks4, http
  host: 127.0.0.1
  port: 9050
  
  # Authentication (optional)
  username: ""
  password: ""
  
  # Tor identity rotation
  rotate_enabled: true
  rotate_interval: 300         # Seconds between rotations
  control_port: 9051
  control_password: ""
```

---

## Output Configuration

```yaml
output:
  default_format: json         # json, md, or both
  pretty_print: true           # Format JSON with indentation
  results_dir: ~/.sherlockml/results
  flags_file: ~/.sherlockml/flags.json
  
  # Graphviz settings
  graph_format: svg            # svg, png, pdf
  graph_rankdir: LR            # LR (left-right) or TB (top-bottom)
```

---

## CTF-Specific Configuration

```yaml
ctf:
  auto_detect_format: true     # Auto-detect flag formats
  fast_fail: false             # Stop on first flag
  
  # Custom flag patterns (regex)
  flag_patterns:
    - '(flag|ctf|glug|hxp|picoCTF|HTB)\{[^}]+\}'
    - 'FLAG\{[^}]+\}'
    - 'CTF_[A-Za-z0-9_]+_[A-Za-z0-9]+'
  
  # Priority platforms for CTF (checked first)
  priority_platforms:
    - pastebin
    - github
    - keybase
    - hackernews
```

---

## Logging Configuration

```yaml
logging:
  level: INFO                  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: ~/.sherlockml/sherlockml.log
  rotate_size: 10485760        # 10MB
  backup_count: 5
```

---

## Environment Variable Expansion

Config values can reference environment variables:

```yaml
platforms:
  github:
    auth_token: ${GITHUB_TOKEN}
    
  twitter:
    auth_token: ${TWITTER_BEARER_TOKEN:-}  # With default empty value
```

Set variables before running:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
export TWITTER_BEARER_TOKEN=AAAAxxxxxxxx
sherlockml search username
```

---

## Example Configurations

### Minimal CTF Config

```yaml
platforms:
  github:
    enabled: true
    auth_token: ${GITHUB_TOKEN}
  pastebin:
    enabled: true
  hackernews:
    enabled: true

ctf:
  fast_fail: true
  flag_patterns:
    - 'flag\{[^}]+\}'
```

### Privacy-Focused Config

```yaml
proxy:
  enabled: true
  type: socks5
  host: 127.0.0.1
  port: 9050
  rotate_enabled: true
  rotate_interval: 180

search:
  max_concurrent: 3            # Lower concurrency
  default_rate_limit: 2.0      # Slower rate

output:
  results_dir: /tmp/sherlockml  # Ephemeral storage
```

### Team/Enterprise Config

```yaml
ml:
  vectorstore_type: qdrant
  qdrant_host: qdrant.internal
  qdrant_port: 6333

search:
  max_concurrent: 20
  
logging:
  level: INFO
  file: /var/log/sherlockml/app.log
```
