# SherlockML

**Production-ready OSINT framework for CTF competitions** combining Sherlock-style username enumeration with Machine Learning, RAG, and Reinforcement Learning.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **Smart Enumeration**: Search 95 built-in platforms with async parallelism
- 🌐 **Active Search**: Aggressive default variant generation (reversed parts, initial forms, digit suffixes) ranked by Jaro-Winkler similarity, plus `--variants` for full expansion (leet, prefixes, suffixes)
- 🕸️ **Cross-Platform Discovery** (`--deep`): Multi-hop traversal across ~28 platform URL patterns + bare `@handle` mentions in bios. Tunable depth via `--max-hops` and `--max-discovered`
- 📇 **Contact Harvesting**: Non-role email addresses are auto-extracted from found profile pages and surfaced in the report
- 🌍 **International Coverage**: Chinese, Russian, Japanese, Korean, and European platforms
- 🛡️ **Advanced False Positive Detection**: Soft 404s, empty pages, login walls, redirect detection, and multilingual "not found" patterns
- 🤖 **LLM Profile Verification**: Use OpenAI, Anthropic, Gemini, or local models to verify if found accounts are real or empty
- 🧠 **ML-Powered**: RAG for semantic search, RL for platform prioritization
- 🚩 **CTF-Optimized**: Flag detection, fast-fail mode, writeup generation
- 🔗 **Social Graphing**: Build relationship networks with NetworkX
- 📊 **Rich Output**: JSON reports, Graphviz diagrams, Markdown writeups
- 🐳 **Docker Ready**: Multi-stage build with Tor support
- ✅ **Well-Tested**: 173 tests covering variant generation, URL/handle/email/flag extraction, reporters, and platform pattern regressions

## Quick Start

```bash
# Install
pip install -e .

# Initialize config
sherlockml init

# Search for a username (auto-generates basic variants by default)
sherlockml search john_doe --max-time 60

# Cross-platform discovery: follow URL links and @handle mentions on
# found profiles up to N hops, also harvest emails from profile pages
sherlockml search john_doe --deep --max-hops 2

# Search and verify profiles with LLM
sherlockml search john_doe --verify --llm-key sk-...

# Generate username variants
sherlockml generate-variants john_doe --leet --years 2020-2025

# Deep GitHub scan
sherlockml scan-github targetuser --commits --depth 20

# Wayback Machine analysis
sherlockml wayback https://example.com --scan-content --diff
sherlockml wayback john_doe --mode profile --scan-content
sherlockml wayback example.com --mode domain --scan-content
```

## Installation

### From Source

```bash
git clone https://github.com/sherlockml/sherlockml.git
cd sherlockml
pip install -e ".[dev]"

# Download SpaCy model
python -m spacy download en_core_web_sm
```

### Docker

```bash
docker build -t sherlockml .
docker run -v ~/.sherlockml:/root/.sherlockml sherlockml search targetuser
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `search <username>` | Search across all platforms |
| `generate-variants <username>` | Generate username permutations |
| `scan-github <username>` | Deep GitHub enumeration |
| `wayback <target>` | Query Wayback Machine for historical data |
| `rag-query <query>` | Semantic search indexed data |
| `rl-train --dataset <file>` | Train platform prioritization |
| `init` | Initialize configuration |

### Search Options

```bash
sherlockml search john_doe \
  --max-time 120 \         # Timeout in seconds
  --output results.json \
  --format both \          # json, md, or both
  --fast-fail \            # Stop on first flag
  --variants \             # Full variant expansion (leet, prefixes, suffixes)
  --deep \                 # Cross-platform discovery from found profiles
  --max-hops 2 \           # Discovery depth (default 2; only with --deep)
  --max-discovered 15 \    # Total discovered username cap (only with --deep)
  --rate-limit 10 \        # Requests per second
  --verify                 # LLM verification of found profiles
```

## Configuration

Config location: `~/.sherlockml/config.yaml`

```yaml
platforms:
  github:
    enabled: true
    priority_weight: 0.92
    auth_token: ${GITHUB_TOKEN}
  twitter:
    enabled: true
    priority_weight: 0.78

ml:
  rag_threshold: 0.75
  rl_learning_rate: 0.1

search:
  max_concurrent: 25
  request_timeout: 15

llm:
  enabled: true
  provider: openai         # openai, anthropic, gemini, or openai-compatible
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini

proxy:
  enabled: false
  type: socks5
  host: 127.0.0.1
  port: 9050
```

## Architecture

```
sherlockml/
├── enum/           # Enumeration engine
│   ├── platform_base.py  # Platform interface + false positive detection
│   ├── variants.py     # Username generation
│   ├── orchestrator.py # Async search + confidence adjustment
│   ├── verify.py       # LLM-powered profile verification
│   └── registry.py     # Platform plugin system
├── ml/             # Machine learning
│   ├── rag_pipeline.py # Vector search (ChromaDB)
│   ├── rl_controller.py # Thompson Sampling
│   └── ner_extractor.py # Entity extraction
├── extract/        # Data extractors
│   ├── github_scanner.py
│   ├── wayback.py
│   └── social_parser.py
├── output/         # Reporters
│   ├── json_reporter.py
│   ├── graphviz_export.py
│   └── markdown_writer.py
└── platforms/      # Built-in platforms (95)
```

## CTF Features

- **Flag Detection**: Auto-detect `flag{...}`, `CTF{...}`, `picoCTF{...}`, etc.
- **Fast-Fail Mode**: Stop searching after first flag found
- **Writeup Generation**: Auto-generate Markdown CTF writeups
- **Team Sharing**: Export flags to `flags.json`
- **Time Travel**: Full Wayback Machine CLI with URL, profile, and domain scan modes

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy sherlockml/

# Linting
ruff check sherlockml/
```

## Deployment (Ansible)

```bash
cd ansible
ansible-playbook -i inventory playbook.yml \
  --extra-vars "github_token=ghp_xxx"
```

## Performance

- 95 platforms with 20 variants: < 4 minutes
- Vectorstore query latency: < 100ms
- RL model update: < 1s per feedback
- Memory footprint: < 500MB base

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Note**: This tool is for authorized security research and CTF competitions only. Always obtain proper permission before scanning third-party systems.
