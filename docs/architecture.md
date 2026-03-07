# System Architecture

SherlockML is designed as a modular, extensible OSINT framework with ML-powered intelligence.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI Interface                               │
│                           (click + rich)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Enumeration    │     │   ML Core       │     │  Data Extract   │
│  Engine         │     │                 │     │                 │
│ ┌─────────────┐ │     │ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │ Orchestrator│ │     │ │ RAG Pipeline│ │     │ │ GitHub Scan │ │
│ └─────────────┘ │     │ └─────────────┘ │     │ └─────────────┘ │
│ ┌─────────────┐ │     │ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │ Platform Reg│ │     │ │ RL Control  │ │     │ │ Wayback     │ │
│ └─────────────┘ │     │ └─────────────┘ │     │ └─────────────┘ │
│ ┌─────────────┐ │     │ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │ Variants    │ │     │ │ NER Extract │ │     │ │ Social Graph│ │
│ └─────────────┘ │     │ └─────────────┘ │     │ └─────────────┘ │
└─────────────────┘     └─────────────────┘     └─────────────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │    Output Formatters    │
                       │ (JSON, Graphviz, MD)    │
                       └─────────────────────────┘
```

## Module Structure

```
sherlockml/
├── __init__.py           # Package init, version
├── config.py             # Pydantic configuration
├── cli.py                # Click CLI interface
│
├── enum/                 # Enumeration Engine
│   ├── variants.py       # Username generation
│   ├── platform_base.py  # Abstract platform interface + false positive detection
│   ├── registry.py       # Plugin system
│   ├── orchestrator.py   # Async search + confidence adjustment
│   └── verify.py         # LLM-powered profile verification
│
├── platforms/            # Built-in Platforms (93)
│   ├── github.py         # Social, Code, Video, Gaming,
│   ├── twitter.py        # Creative, Music, Professional,
│   ├── reddit.py         # Forum, CTF/Security, and more
│   └── ... (93 platforms across 12 categories, including international)
│
├── ml/                   # Machine Learning
│   ├── rag_pipeline.py   # Vector search
│   ├── rl_controller.py  # Platform prioritization
│   └── ner_extractor.py  # Entity extraction
│
├── extract/              # Data Extractors
│   ├── github_scanner.py # Deep GitHub analysis
│   ├── wayback.py        # Internet Archive
│   └── social_parser.py  # Social graph building
│
└── output/               # Output Formatters
    ├── json_reporter.py  # JSON with confidence
    ├── graphviz_export.py # DOT graphs
    └── markdown_writer.py # CTF writeups
```

---

## Core Components

### 1. Configuration System

**File:** `sherlockml/config.py`

Pydantic-based configuration with YAML loading and environment variable expansion.

```python
from sherlockml.config import load_config, Config

config = load_config()  # Loads ~/.sherlockml/config.yaml
print(config.platforms.github.enabled)
```

**Key Classes:**
- `Config` - Root configuration model
- `PlatformConfig` - Per-platform settings
- `MLConfig` - ML component settings
- `SearchConfig` - Search behavior settings
- `LLMConfig` - LLM verification settings (provider, API key, model)

### 2. Enumeration Engine

**Files:** `sherlockml/enum/`

#### UsernameVariants

Generates username permutations with:
- Leetspeak substitution (a→4, e→3, etc.)
- Common prefixes/suffixes (real, the, _official)
- Year suffixes (2020-2025)
- Separator variants (_, ., -)
- Jaro-Winkler fuzzy matching

```python
from sherlockml.enum.variants import UsernameVariants

gen = UsernameVariants()
variants = gen.generate("johndoe", leet=True, years=(2020, 2025))
```

#### Orchestrator

Manages concurrent async searches with:
- Semaphore-controlled parallelism (configurable max)
- Per-platform rate limiting
- Proxy support (SOCKS5, Tor)
- Timeout handling
- Flag detection
- Low-confidence tagging for borderline positive results (checks for profile indicators like images, username mentions, and sufficient text content)

```python
from sherlockml.enum.orchestrator import Orchestrator

orchestrator = Orchestrator(config)
results = await orchestrator.search(usernames, platforms)
```

#### PlatformRegistry

Dynamic plugin loading from:
- Built-in platforms (`sherlockml/platforms/`)
- User plugins (`~/.sherlockml/plugins/`)

```python
from sherlockml.enum.registry import get_registry

registry = get_registry()
platforms = registry.get_enabled(config)
```

### 3. Machine Learning Core

**Files:** `sherlockml/ml/`

#### RAGPipeline

Semantic search using:
- ChromaDB for vector storage
- Sentence Transformers for embeddings
- Incremental indexing

```python
from sherlockml.ml.rag_pipeline import RAGPipeline

rag = RAGPipeline(vectorstore_path)
rag.index("document content", metadata={"platform": "github"})
results = rag.query("find email addresses", top_k=10)
```

#### RLController

Thompson Sampling multi-armed bandit for platform prioritization:
- Tracks success/failure per platform
- Balances exploration vs exploitation
- Persists weights in SQLite

```python
from sherlockml.ml.rl_controller import RLController

with RLController(weights_db_path) as rl:
    platforms = rl.select_platforms(available, n=5)
    rl.update("github", flag_found=True, response_time=0.5)
```

#### NERExtractor

Entity extraction combining:
- SpaCy for general NER
- Custom regex for CTF-specific patterns (flags, hashes, IPs)

```python
from sherlockml.ml.ner_extractor import NERExtractor

ner = NERExtractor()
entities = ner.extract(text)
print(entities.flags, entities.emails)
```

### 4. Data Extractors

**Files:** `sherlockml/extract/`

#### GitHubScanner

Deep GitHub enumeration:
- Commit history search
- Email extraction from commits
- Gist scanning
- Sensitive file detection

#### WaybackIntegration

Internet Archive CDX API:
- Historical snapshots
- robots.txt/sitemap.xml extraction
- Hidden endpoint discovery

#### SocialMediaParser

Social graph analysis:
- rel="me" link extraction
- Platform detection from URLs
- NetworkX graph building
- PageRank centrality

### 5. Output Formatters

**Files:** `sherlockml/output/`

| Formatter | Output | Use Case |
|-----------|--------|----------|
| JSONReporter | JSON with confidence | Machine-readable results |
| GraphvizExporter | DOT format | Social network visualization |
| MarkdownWriter | MD writeup | CTF documentation |

---

## Data Flow

```
1. User Input
   └── username: "johndoe"

2. Variant Generation
   └── ["johndoe", "j0hndoe", "johndoe2024", ...]

3. Platform Selection (RL-powered)
   └── [github, twitter, reddit, ...] ordered by expected value

4. Parallel Search (Orchestrator)
   ├── Rate limiting
   ├── Proxy rotation
   └── Timeout handling

5. Result Processing
   ├── False positive filtering (soft 404, empty pages, redirects, login walls)
   ├── Low-confidence tagging for borderline results
   ├── NER extraction
   ├── Flag detection
   └── Confidence scoring

5b. LLM Verification (optional, --verify)
   ├── Strip HTML to text for each found profile
   ├── Send to LLM (OpenAI/Anthropic/Gemini/local)
   └── Classify as real / empty / suspicious

6. RAG Indexing
   └── Store in vectorstore for future queries

7. Output Generation
   └── JSON, GraphML, Markdown
```

---

## Async Architecture

SherlockML uses `asyncio` for non-blocking I/O:

```python
async def search_flow():
    async with aiohttp.ClientSession() as session:
        # Semaphore limits concurrent requests
        semaphore = asyncio.Semaphore(25)

        tasks = [
            asyncio.create_task(
                check_platform(platform, username, session, semaphore)
            )
            for platform in platforms
            for username in usernames
        ]

        # Process results as they complete
        for coro in asyncio.as_completed(tasks):
            result = await coro
            process_result(result)
```

### Rate Limiting

Interval-based rate limiting per platform using asyncio locks:

```python
async def _rate_limit(self, platform_name: str, rate_limit: float) -> None:
    async with self._rate_limiters[platform_name]:
        min_interval = 1.0 / rate_limit
        elapsed = time.monotonic() - self._last_request.get(platform_name, 0)
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request[platform_name] = time.monotonic()
```

---

## Plugin System

### Creating a Custom Platform

```python
# ~/.sherlockml/plugins/my_platform.py
from sherlockml.enum.platform_base import BasePlatform, PlatformResult, PlatformCategory

class MyPlatform(BasePlatform):
    name = "myplatform"
    display_name = "My Platform"
    base_url = "https://myplatform.com"
    url_template = "https://myplatform.com/users/{username}"
    category = PlatformCategory.OTHER
    rate_limit_rpm = 30.0

    def validate_username(self, username: str) -> bool:
        return len(username) >= 3

    async def check_username(self, username: str, session) -> PlatformResult:
        url = self.get_url(username)
        async with session.get(url) as resp:
            return PlatformResult(
                exists=resp.status == 200,
                url=url,
            )
```

The plugin is automatically discovered and loaded.

---

## Security Considerations

1. **Credential Storage**: API tokens stored in environment variables
2. **Rate Limiting**: Built-in to prevent API abuse
3. **Proxy Support**: Tor integration for anonymization
4. **Non-root Docker**: Container runs as unprivileged user
