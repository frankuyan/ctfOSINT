# Getting Started

This guide will help you install SherlockML and run your first OSINT search.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Optional: Docker for containerized deployment

## Installation

### Method 1: From Source (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/sherlockml.git
cd sherlockml

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Download required SpaCy model
python -m spacy download en_core_web_sm
```

### Method 2: Docker (Recommended for Production)

```bash
# Clone and build
git clone https://github.com/yourusername/sherlockml.git
cd sherlockml

# Copy environment file and configure
cp docker/.env.example .env
# Edit .env with your API tokens

# Build and start
docker-compose up -d

# Run commands
docker-compose exec sherlockml sherlockml search targetuser
```

### Method 3: pip Install

```bash
pip install sherlockml
python -m spacy download en_core_web_sm
```

## Initial Configuration

Initialize your configuration file:

```bash
sherlockml init
```

This creates `~/.sherlockml/config.yaml` with default settings.

### Adding API Tokens

For best results, add API tokens to your config:

```yaml
# ~/.sherlockml/config.yaml
platforms:
  github:
    enabled: true
    auth_token: ${GITHUB_TOKEN}  # Set env var or paste token
```

Or use environment variables:

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

## Your First Search

### Basic Search

```bash
sherlockml search johndoe
```

This searches for "johndoe" across all enabled platforms.

### Search with Options

```bash
# Search with 2-minute timeout and save results
sherlockml search johndoe --max-time 120 --output results.json

# Generate username variants automatically
sherlockml search johndoe --variants

# Stop on first CTF flag found
sherlockml search johndoe --fast-fail

# Use Tor proxy
sherlockml search johndoe --proxy socks5://127.0.0.1:9050
```

### Understanding Output

```
SherlockML v1.0.0
Searching for johndoe (15 variants)

Platforms: 10 enabled
  ✓ github: https://github.com/johndoe
  ✓ twitter: https://twitter.com/johndoe
  ✓ reddit: https://reddit.com/u/johndoe

Results:
  Platforms checked: 10
  Profiles found: 3
  Flags found: 0
  Time: 12.4s

Saved JSON: sherlockml_johndoe.json
```

## Next Steps

- Learn all CLI commands: [CLI Reference](cli-reference.md)
- Configure platforms: [Configuration](configuration.md)
- CTF-specific tips: [CTF Playbook](ctf-playbook.md)
- Deploy at scale: [Docker Deployment](docker-deployment.md)

## Getting Help

```bash
# General help
sherlockml --help

# Command-specific help
sherlockml search --help
```
