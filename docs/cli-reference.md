# CLI Reference

Complete command-line interface documentation for SherlockML.

## Global Options

```bash
sherlockml [OPTIONS] COMMAND [ARGS]...
```

| Option | Short | Description |
|--------|-------|-------------|
| `--config PATH` | `-c` | Path to config file (default: ~/.sherlockml/config.yaml) |
| `--verbose` | `-v` | Enable verbose output |
| `--version` | | Show version and exit |
| `--help` | | Show help message |

---

## Commands

### search

Search for a username across all enabled platforms.

```bash
sherlockml search [OPTIONS] USERNAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `USERNAME` | Target username to search for (required) |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--max-time` | `-t` | INT | 90 | Maximum search time in seconds |
| `--output` | `-o` | PATH | - | Output file path |
| `--format` | `-f` | CHOICE | json | Output format: json, md, or both |
| `--fast-fail` | | FLAG | false | Stop after first flag found |
| `--rate-limit` | `-r` | FLOAT | - | Global requests per second |
| `--proxy` | | TEXT | - | Proxy URL (socks5://host:port) |
| `--wordlist` | `-w` | PATH | - | File with additional usernames |
| `--variants` | | FLAG | false | Full variant expansion (leet, prefixes, suffixes) |
| `--no-variants` | | FLAG | false | Disable automatic basic variant generation |
| `--deep` | | FLAG | false | Cross-platform discovery: search linked usernames found in profiles |
| `--max-hops` | | INT | 2 | Discovery depth (only with `--deep`). 1 = direct links of seeds; 2 = also follow links of discovered profiles |
| `--max-discovered` | | INT | 15 | Maximum total discovered usernames across all hops (only with `--deep`) |
| `--verify` | | FLAG | false | Use LLM to verify found profiles are real |
| `--llm-key` | | TEXT | - | LLM API key (overrides config, env: SHERLOCKML_LLM_KEY) |

**Examples:**

```bash
# Basic search (automatically generates separator/case variants)
# e.g. john_doe -> johndoe, john.doe, john-doe, jdoe
sherlockml search john_doe

# Search exact username only (no variants)
sherlockml search john_doe --no-variants

# Full variant expansion (leet, prefixes, suffixes)
sherlockml search john_doe --variants --fast-fail

# Deep mode: discover and search linked usernames from found profiles
sherlockml search john_doe --deep --max-time 120 -o results.json

# Search through proxy
sherlockml search johndoe --proxy socks5://127.0.0.1:9050

# Search with custom wordlist
sherlockml search johndoe -w usernames.txt

# Search and verify profiles with LLM (OpenAI)
# Shows OSINT details: bio, join date, activity, links, notable info
sherlockml search johndoe --verify --llm-key sk-...

# Verify with Gemini (set provider in config)
sherlockml search johndoe --verify --llm-key AIza...

# Verify using config API key
sherlockml search johndoe --verify
```

**Username Variant Behavior:**

By default, SherlockML generates up to ~15 high-quality variants from the input username, ranked by Jaro-Winkler similarity. For `john_doe` this includes separator swaps (`johndoe`, `john.doe`, `john-doe`), case changes, reversed parts (`doe_john`, `doejohn`), first-initial and reverse-initial forms (`jdoe`, `johnd`), and light digit suffixes (`johndoe1`, `johndoe2024`). For a single-part input like `alice`, default variants are the digit-suffix forms (`alice1`, `alice01`, `alice2024`, `alice2025`).

- **Default**: Basic similarity-ranked variants (separators, case, reversed parts, initials, light digit suffixes) — up to 15
- **`--variants`**: Full expansion with leetspeak, common prefixes/suffixes, and a wider year sweep (up to 20 extra, also ranked by similarity)
- **`--no-variants`**: Search only the exact username entered (mutually exclusive with `--variants`)
- **`--deep`**: Cross-platform discovery — when a profile is found, extract linked usernames and bare `@handle` mentions from the profile page and search those too. By default follows up to 2 hops (seeds → linked profiles → links of those profiles), capped at 15 total discovered usernames. Tune with `--max-hops` and `--max-discovered`.

When a profile is found, SherlockML also harvests any non-role email addresses (`alice@protonmail.com`, skipping `noreply@`/`support@`/etc.) from the profile page and surfaces them in a `Contacts` section of the result.

When `--verify` is used, results are split into two tables:
- **Verified Profiles**: Real/suspicious accounts with extracted OSINT details (bio, display name, join date, activity, external links, notable info).
- **Empty / Default Pages**: Compact list of platforms with no real content.

---

### generate-variants

Generate username permutations from a base username.

```bash
sherlockml generate-variants [OPTIONS] BASE_USERNAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `BASE_USERNAME` | Base username to generate variants from |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--leet` | | FLAG | false | Include leetspeak variants |
| `--years` | | TEXT | - | Year range (e.g., 2015-2025) |
| `--common` | | FLAG | false | Include common prefixes/suffixes |
| `--output` | `-o` | PATH | - | Save variants to file |
| `--max` | `-n` | INT | 100 | Maximum variants to generate |

**Examples:**

```bash
# Basic variant generation
sherlockml generate-variants johndoe

# With leetspeak and years
sherlockml generate-variants johndoe --leet --years 2020-2025

# Save to file
sherlockml generate-variants johndoe --leet --common -o variants.txt -n 200
```

**Sample Output:**

```
Generated 47 variants for 'johndoe'

  johndoe
  JOHNDOE
  j0hndoe
  johndoe2024
  johndoe_
  thejohndoe
  realjohndoe
  ...
```

---

### scan-github

Deep GitHub enumeration for a specific user.

```bash
sherlockml scan-github [OPTIONS] USERNAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `USERNAME` | GitHub username to scan |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--commits` | | FLAG | false | Search commit history |
| `--gists` | | FLAG | true | Include public gists |
| `--depth` | `-d` | INT | 10 | Search depth (pages) |
| `--output` | `-o` | PATH | - | Save results to file |

**Examples:**

```bash
# Basic scan
sherlockml scan-github targetuser

# Deep commit scanning
sherlockml scan-github targetuser --commits --depth 50

# Save results
sherlockml scan-github targetuser --commits -d 20 -o github_results.json
```

**What It Finds:**

- Public repositories
- Commit history with email addresses
- Public gists
- CTF flags in commit messages
- Sensitive file patterns

---

### rag-query

Query the semantic search vectorstore.

```bash
sherlockml rag-query [OPTIONS] QUERY
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `QUERY` | Natural language search query |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--top-k` | `-k` | INT | 5 | Number of results |
| `--threshold` | `-t` | FLOAT | 0.0 | Minimum similarity score |

**Examples:**

```bash
# Basic query
sherlockml rag-query "emails related to target"

# Query with more results
sherlockml rag-query "github commit messages" -k 20

# Query with threshold
sherlockml rag-query "CTF flags" -k 10 -t 0.7
```

---

### rl-train

Train the RL model on historical CTF data.

```bash
sherlockml rl-train [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--dataset` | `-d` | PATH | - | JSON file with training data (required) |
| `--epochs` | `-e` | INT | 50 | Number of training epochs |

**Dataset Format:**

```json
[
  {
    "challenge": "osint_001",
    "platforms": {
      "github": true,
      "twitter": false,
      "pastebin": true
    }
  }
]
```

**Examples:**

```bash
# Train on CTF dataset
sherlockml rl-train -d past_ctfs.json -e 100
```

---

### wayback

Query the Wayback Machine for historical OSINT data.

```bash
sherlockml wayback [OPTIONS] TARGET
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `TARGET` | URL, username, or domain depending on `--mode` |

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--mode` | `-m` | CHOICE | url | Scan mode: url, profile, or domain |
| `--from-date` | | TEXT | - | Start date (YYYY or YYYYMMDD) |
| `--to-date` | | TEXT | - | End date (YYYY or YYYYMMDD) |
| `--scan-content` | `-s` | FLAG | false | Fetch and scan snapshot content for flags |
| `--diff` | `-d` | FLAG | false | Show differences between snapshots |
| `--platforms` | `-p` | TEXT | - | Comma-separated platform names (profile mode) |
| `--max-snapshots` | | INT | 5 | Max snapshots to fetch content from |
| `--output` | `-o` | PATH | - | Output file (JSON) |
| `--rate-limit` | `-r` | FLOAT | 10.0 | Requests per minute to Wayback API |

**Modes:**

- **url** - Analyze a single URL: snapshots, robots.txt, sitemap, hidden endpoints, flag scanning
- **profile** - Scan a username's archived profiles across 27 platforms
- **domain** - Wildcard discovery of all archived pages under a domain

**Examples:**

```bash
# Analyze a single URL's history
sherlockml wayback https://example.com/user --scan-content

# Scan with snapshot diffing to find changes
sherlockml wayback https://ctf-site.com/challenge --from-date 2023 --diff

# Find archived profiles for a username
sherlockml wayback john_doe --mode profile --scan-content

# Check specific platforms only
sherlockml wayback john_doe --mode profile -p github,twitter,pastebin -s

# Wildcard domain scan for hidden files
sherlockml wayback challenge-site.com --mode domain -s

# Save results to JSON
sherlockml wayback https://example.com -s -o wayback_results.json
```

**What It Finds:**

- Historical snapshots with timestamps and Wayback URLs
- Hidden endpoints from robots.txt (admin, api, backup, .git, .env, etc.)
- Sitemap URLs from archived sitemap.xml
- CTF flags in archived page content
- Content changes between snapshots (diff mode)
- Deleted profiles and old bios (profile mode)
- Forgotten files like flag.txt, .env, .bak, .sql (domain mode)

---

### init

Initialize SherlockML configuration.

```bash
sherlockml init [OPTIONS]
```

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--force` | `-f` | FLAG | false | Overwrite existing config |

**Examples:**

```bash
# Create default config
sherlockml init

# Overwrite existing config
sherlockml init --force
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Network/timeout error |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub API token |
| `TWITTER_BEARER_TOKEN` | Twitter API bearer token |
| `SHERLOCKML_CONFIG` | Override config file path |
| `SHERLOCKML_DATA` | Data directory path |
| `SHERLOCKML_LLM_KEY` | LLM API key for profile verification |
| `OPENAI_API_KEY` | OpenAI API key (used by LLM config) |
| `ANTHROPIC_API_KEY` | Anthropic API key (used by LLM config) |
| `GEMINI_API_KEY` | Google Gemini API key (used by LLM config) |
