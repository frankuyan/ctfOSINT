# SherlockML

**Production-ready OSINT framework for CTF competitions** combining Sherlock-style username enumeration with Machine Learning, RAG, and Reinforcement Learning.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **Smart Enumeration**: Search 70 built-in platforms with async parallelism
- 🧠 **ML-Powered**: RAG for semantic search, RL for platform prioritization
- 🚩 **CTF-Optimized**: Flag detection, fast-fail mode, writeup generation
- 🔗 **Social Graphing**: Build relationship networks with NetworkX
- 📊 **Rich Output**: JSON reports, Graphviz diagrams, Markdown writeups
- 🐳 **Docker Ready**: Multi-stage build with Tor support

## Quick Start

```bash
# Install
pip install -e .

# Initialize config
sherlockml init

# Search for a username
sherlockml search john_doe --max-time 60

# Generate username variants
sherlockml generate-variants john_doe --leet --years 2020-2025

# Deep GitHub scan
sherlockml scan-github targetuser --commits --depth 20
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
| `rag-query <query>` | Semantic search indexed data |
| `rl-train --dataset <file>` | Train platform prioritization |
| `init` | Initialize configuration |

### Search Options

```bash
sherlockml search john_doe \
  --max-time 120 \      # Timeout in seconds
  --output results.json \
  --format both \       # json, md, or both
  --fast-fail \         # Stop on first flag
  --variants \          # Auto-generate variants
  --rate-limit 10       # Requests per second
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
│   ├── variants.py     # Username generation
│   ├── orchestrator.py # Async search coordination
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
└── platforms/      # Built-in platforms (70)
```

## CTF Features

- **Flag Detection**: Auto-detect `flag{...}`, `CTF{...}`, `picoCTF{...}`, etc.
- **Fast-Fail Mode**: Stop searching after first flag found
- **Writeup Generation**: Auto-generate Markdown CTF writeups
- **Team Sharing**: Export flags to `flags.json`
- **Time Travel**: Query Wayback Machine for historical data

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

- 70 platforms with 20 variants: < 3 minutes
- Vectorstore query latency: < 100ms
- RL model update: < 1s per feedback
- Memory footprint: < 500MB base

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Note**: This tool is for authorized security research and CTF competitions only. Always obtain proper permission before scanning third-party systems.
