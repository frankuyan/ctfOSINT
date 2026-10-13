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
llm: {}            # LLM profile verification settings
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
    priority_weight: 0.88
    auth_token: ${TWITTER_BEARER_TOKEN}
    rate_limit: 5.0
```

#### Mastodon

```yaml
platforms:
  mastodon:
    enabled: true
    priority_weight: 0.85
```

#### LinkedIn

```yaml
platforms:
  linkedin:
    enabled: true
    priority_weight: 0.65
```

### All Built-in Platforms (95 total)

#### Tier 1: High Priority (>0.80 weight)

| Platform | Default Weight | Rate Limit | Auth Required |
|----------|---------------|------------|---------------|
| github | 0.92 | 30/min | Optional |
| gist | 0.88 | 10/min | Optional |
| keybase | 0.88 | 10/min | No |
| gitlab | 0.85 | 20/min | Optional |
| pastebin | 0.85 | 5/min | No |
| tryhackme | 0.85 | 5/min | No |
| hackthebox | 0.85 | 3/min | No |
| hackernews | 0.80 | 10/min | No |
| bitbucket | 0.80 | 10/min | No |
| reddit | 0.90 | 10/min | No |
| twitter | 0.88 | 5/min | Optional |
| mastodon | 0.85 | 10/min | No |
| bluesky | 0.85 | 5/min | No |

#### Tier 2: Medium Priority (0.60-0.80 weight)

| Platform | Default Weight | Rate Limit | Auth Required |
|----------|---------------|------------|---------------|
| dockerhub | 0.78 | 10/min | No |
| npm | 0.75 | 10/min | No |
| pypi | 0.75 | 10/min | No |
| stackoverflow | 0.75 | 5/min | No |
| hackerone | 0.72 | 3/min | No |
| devto | 0.70 | 10/min | No |
| gitea | 0.70 | 10/min | No |
| youtube | 0.70 | 5/min | No |
| linkedin | 0.65 | 2/min | No |
| medium | 0.65 | 5/min | No |
| rubygems | 0.65 | 10/min | No |
| cratesio | 0.65 | 10/min | No |
| kaggle | 0.65 | 5/min | No |
| lobsters | 0.65 | 5/min | No |
| telegram | 0.65 | 3/min | No |
| instagram | 0.60 | 3/min | No |
| codepen | 0.60 | 5/min | No |
| leetcode | 0.60 | 5/min | No |
| codeforces | 0.60 | 5/min | No |
| hashnode | 0.60 | 5/min | No |
| tiktok | 0.60 | 3/min | No |
| twitch | 0.60 | 5/min | No |
| substack | 0.60 | 5/min | No |
| steam | 0.60 | 5/min | No |
| gravatar | 0.60 | 10/min | No |
| gitee | 0.60 | 60/min | No |

#### Tier 3: Standard Priority (0.40-0.60 weight)

| Platform | Default Weight | Rate Limit | Auth Required |
|----------|---------------|------------|---------------|
| discord | 0.55 | 2/min | No |
| threads | 0.55 | 3/min | No |
| replit | 0.55 | 5/min | No |
| soundcloud | 0.55 | 5/min | No |
| spotify | 0.55 | 5/min | No |
| wordpress | 0.55 | 5/min | No |
| patreon | 0.55 | 3/min | No |
| trello | 0.55 | 5/min | No |
| producthunt | 0.55 | 5/min | No |
| linktree | 0.55 | 5/min | No |
| csdn | 0.55 | 30/min | No |
| habr | 0.55 | 30/min | No |
| qiita | 0.55 | 60/min | No |
| codewars | 0.55 | 60/min | No |
| hackerrank | 0.55 | 30/min | No |
| snapchat | 0.50 | 3/min | No |
| tumblr | 0.50 | 5/min | No |
| imgur | 0.50 | 5/min | No |
| pinterest | 0.50 | 3/min | No |
| dribbble | 0.50 | 5/min | No |
| behance | 0.50 | 5/min | No |
| roblox | 0.50 | 5/min | No |
| aboutme | 0.50 | 5/min | No |
| slideshare | 0.50 | 5/min | No |
| quora | 0.50 | 3/min | No |
| buymeacoffee | 0.50 | 5/min | No |
| weibo | 0.50 | 30/min | No |
| vk | 0.50 | 30/min | No |
| bilibili | 0.50 | 30/min | No |
| vsco | 0.45 | 15/min | No |
| letterboxd | 0.45 | 15/min | No |
| vimeo | 0.45 | 5/min | No |
| deviantart | 0.45 | 5/min | No |
| xbox | 0.45 | 3/min | No |
| chesscom | 0.45 | 5/min | No |
| lichess | 0.45 | 5/min | No |
| zhihu | 0.45 | 30/min | No |
| note_jp | 0.45 | 30/min | No |
| naver_blog | 0.45 | 30/min | No |
| lastfm | 0.45 | 30/min | No |
| bandcamp | 0.45 | 30/min | No |
| xing | 0.45 | 30/min | No |
| freelancer | 0.45 | 30/min | No |
| fiverr | 0.45 | 30/min | No |
| askfm | 0.40 | 5/min | No |
| dailymotion | 0.40 | 5/min | No |
| wattpad | 0.40 | 5/min | No |
| newgrounds | 0.40 | 5/min | No |
| mixcloud | 0.40 | 5/min | No |
| myanimelist | 0.40 | 30/min | No |
| anilist | 0.40 | 60/min | No |
| osu | 0.40 | 30/min | No |
| pikabu | 0.40 | 30/min | No |
| baidu_tieba | 0.40 | 20/min | No |
| douyin | 0.40 | 20/min | No |

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
  max_concurrent: 25           # Max parallel requests (1-100)
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

  # Tor identity rotation: SIGNAL NEWNYM on the control port at the start
  # of each search/wayback/scan-github run and every rotate_interval seconds
  rotate: false
  rotate_interval: 300         # seconds; minimum 10 (Tor's NEWNYM rate limit)
  control_port: 9051           # Tor ControlPort on the same host as the proxy
  control_password: ${TOR_CONTROL_PASSWORD}  # only for HashedControlPassword
  rotate_enabled: true         # kill switch: false disables rotation entirely
```

**All target-facing traffic uses this proxy**: search, `--verify` page
fetches, `wayback` and `scan-github`. `--proxy URL` on any of those
commands overrides it. `type: tor` and `socks5h` are accepted as aliases for
`socks5`; SOCKS5 already resolves DNS through the proxy.

**Identity rotation** needs Tor's control port enabled. In `torrc`, pick one:

```
ControlPort 9051
# Option 1: password auth. Generate the hash with: tor --hash-password 'secret'
# and set proxy.control_password to the same secret.
HashedControlPassword 16:...
# Option 2: cookie auth. SherlockML reads the cookie file Tor reports,
# so it must be readable by the user running sherlockml.
CookieAuthentication 1
```

While rotating, HTTP keep-alive is turned off so each request opens a new Tor
stream and picks up the new circuits. If the control port is unreachable or
rejects authentication, one warning is logged and the run continues without
rotating.

---

## Output Configuration

```yaml
output:
  default_format: json         # json, markdown, graphviz
  pretty_print: true           # Format JSON with indentation
  include_raw_responses: false  # Include raw HTTP responses in output (stripped by default to avoid leaking PII)
  flags_file: ~/.sherlockml/flags.json
  writeup_template: ~/.sherlockml/templates/writeup.md.j2
```

---

## LLM Verification Configuration

Use an LLM to verify whether found profiles are real accounts with actual content, or empty/default/suspended pages.

```yaml
llm:
  enabled: false               # Enable LLM verification (or use --verify flag)
  provider: openai             # openai, anthropic, gemini, or openai-compatible
  api_key: ${OPENAI_API_KEY}   # API key (supports env var expansion)
  model: gpt-4o-mini           # Model to use
  base_url: null               # Custom endpoint (for Ollama, vLLM, etc.)
  max_tokens: 256              # Max response tokens
  max_concurrent_verifications: 5  # Parallel LLM calls
  verify_found_only: true      # Only verify profiles marked as found
```

### Supported Providers

| Provider | Config Value | API Key Env Var | Example Model |
|----------|-------------|-----------------|---------------|
| OpenAI | `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` | `gemini-2.0-flash` |
| Local/Compatible | `openai-compatible` | - | `llama3` |

### Using Local Models (Ollama, vLLM, LM Studio)

```yaml
llm:
  enabled: true
  provider: openai-compatible
  api_key: not-needed
  model: llama3
  base_url: http://localhost:11434/v1
```

### Verification Output

When `--verify` is used, each found profile gets an LLM verdict:
- **real**: Genuine account with actual user content
- **empty**: Blank, default, suspended, or deleted page
- **suspicious**: Minimal content, possibly abandoned or placeholder

Results are displayed in a table and included in JSON output under `llm_verdict`, `llm_confidence`, and `llm_reason` metadata fields.

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

**Note:** Environment variable expansion uses `${VAR}` syntax. Undefined variables expand to empty strings and a warning is logged, so you can detect misconfigured tokens or missing secrets early.

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
  rotate: true                 # needs Tor's ControlPort, see Proxy Configuration
  control_password: ${TOR_CONTROL_PASSWORD}

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
