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
| `--variants` | | FLAG | false | Auto-generate username variants |
| `--verify` | | FLAG | false | Use LLM to verify found profiles are real |
| `--llm-key` | | TEXT | - | LLM API key (overrides config, env: SHERLOCKML_LLM_KEY) |

**Examples:**

```bash
# Basic search
sherlockml search johndoe

# Search with timeout and output
sherlockml search johndoe -t 120 -o results.json

# Search with variants and fast-fail
sherlockml search johndoe --variants --fast-fail

# Search through proxy
sherlockml search johndoe --proxy socks5://127.0.0.1:9050

# Search with custom wordlist
sherlockml search johndoe -w usernames.txt

# Search and verify profiles with LLM (OpenAI)
sherlockml search johndoe --verify --llm-key sk-...

# Verify with Gemini (set provider in config)
sherlockml search johndoe --verify --llm-key AIza...

# Verify using config API key
sherlockml search johndoe --verify
```

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
