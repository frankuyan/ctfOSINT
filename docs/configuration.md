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
plugins_dir: ~/.sherlockml/plugins   # Custom plugin directory
data_dir: ~/.sherlockml/data         # Data directory
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
    rate_limit: 30.0           # Per-platform rate limit override (requests/sec)
    search_commits: true       # Enable commit searching
    custom_headers: {}         # Custom HTTP headers
```

### Per-Platform Options

#### GitHub

```yaml
platforms:
  github:
    enabled: true
    priority_weight: 0.92
    auth_token: ${GITHUB_TOKEN}
    search_commits: true       # Enable commit searching
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
```

#### LinkedIn

```yaml
platforms:
  linkedin:
    enabled: true
    priority_weight: 0.65
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
  rag_threshold: 0.75          # Minimum similarity score (0.0-1.0)
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  vectorstore_path: ~/.sherlockml/vectorstore

  # RL (Reinforcement Learning) Settings
  rl_learning_rate: 0.1        # Learning rate for updates (0.0-1.0)
  rl_weights_db: ~/.sherlockml/rl_weights.db

  # NER (Named Entity Recognition) Settings
  ner_model_path: ~/.sherlockml/ner_model  # Custom SpaCy model path
```

---

## Search Configuration

```yaml
search:
  max_concurrent: 10           # Max parallel requests (1-100)
  request_timeout: 15          # Seconds per request (1-120)
  default_rate_limit: 5.0      # Global requests/second (0.1-100)
  retry_attempts: 3            # Retry failed requests (0-10)
  retry_delay: 1.0             # Delay between retries in seconds (0-30)

  # User agent rotation
  user_agents:
    - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    - "SherlockML/1.0 (OSINT Research Tool)"
```

---

## Proxy Configuration

```yaml
proxy:
  enabled: false
  type: socks5                 # socks5, http, tor
  host: 127.0.0.1
  port: 9050

  # Authentication (optional, use env vars for secrets)
  username: ${PROXY_USERNAME}
  password: ${PROXY_PASSWORD}

  # Proxy rotation (when using proxy lists)
  rotate: false
```

---

## Output Configuration

```yaml
output:
  default_format: json         # json, markdown, graphviz
  pretty_print: true           # Format JSON with indentation
  include_raw_responses: false # Include raw HTTP responses
  flags_file: ~/.sherlockml/flags.json
  writeup_template: ~/.sherlockml/templates/writeup.md.j2
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

  # Set search date for historical queries (optional)
  time_travel_date: null
```

---

## Environment Variable Expansion

Config values can reference environment variables:

```yaml
platforms:
  github:
    auth_token: ${GITHUB_TOKEN}

  twitter:
    auth_token: ${TWITTER_BEARER_TOKEN}
```

**Note:** Environment variable expansion uses `${VAR}` syntax. Undefined variables expand to empty strings.

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
  rotate: true

search:
  max_concurrent: 3            # Lower concurrency
  default_rate_limit: 2.0      # Slower rate
```

### Team Config

```yaml
ml:
  vectorstore_path: /shared/sherlockml/vectorstore
  rl_weights_db: /shared/sherlockml/rl_weights.db

search:
  max_concurrent: 20
```
