# API Reference

Python API documentation for SherlockML.

## Installation

```python
pip install sherlockml
```

## Quick Start

```python
import asyncio
from sherlockml.config import load_config
from sherlockml.enum.registry import get_registry
from sherlockml.enum.orchestrator import Orchestrator

async def search_user(username: str):
    config = load_config()
    registry = get_registry()
    platforms = registry.get_enabled(config)

    orchestrator = Orchestrator(config)
    results = await orchestrator.search([username], platforms)

    print(f"Found {results.found_count} profiles")
    for result in results.results:
        if result.exists:
            print(f"  {result.platform}: {result.url}")

asyncio.run(search_user("johndoe"))
```

---

## Configuration

### load_config

```python
from sherlockml.config import load_config, Config

# Load default config (~/.sherlockml/config.yaml)
config = load_config()

# Load custom config
config = load_config("/path/to/config.yaml")

# Create default config
from sherlockml.config import create_default_config_file
create_default_config_file("/path/to/new_config.yaml")
```

### Config Object

```python
config = load_config()

# Access platform settings (returns defaults if not configured)
github_config = config.get_platform("github")
print(github_config.enabled)
print(github_config.priority_weight)

# Access ML settings
print(config.ml.rag_threshold)
print(config.ml.vectorstore_dir)  # Returns expanded Path

# Access search settings
print(config.search.max_concurrent)
print(config.search.request_timeout)
```

---

## Enumeration Engine

### UsernameVariants

```python
from sherlockml.enum.variants import UsernameVariants

gen = UsernameVariants()

# Basic generation
variants = gen.generate("johndoe")
# ['johndoe', 'JOHNDOE', 'Johndoe', ...]

# With leetspeak
variants = gen.generate("johndoe", leet=True)
# [..., 'j0hndoe', 'johnd0e', ...]

# With year suffixes
variants = gen.generate("johndoe", years=(2020, 2025))
# [..., 'johndoe2020', 'johndoe21', ...]

# With common prefixes/suffixes
variants = gen.generate("johndoe", include_common=True)
# [..., 'thejohndoe', 'realjohndoe', 'johndoe_official', ...]

# Limit results
variants = gen.generate("johndoe", leet=True, max_variants=50)

# Fuzzy matching
is_similar = gen.fuzzy_match("johndoe", "john_doe", threshold=0.8)
# True

# Rank by similarity
ranked = gen.rank_by_similarity(variants, "johndoe")
# [('johndoe', 1.0), ('johnd0e', 0.95), ...]
```

### PlatformRegistry

```python
from sherlockml.enum.registry import get_registry

registry = get_registry()

# Get enabled platforms (sorted by priority)
enabled = registry.get_enabled(config)

# Get specific platform instance
github = registry.get("github", auth_token="ghp_xxx")

# List available platform names
names = registry.available_platforms
# ['github', 'twitter', 'reddit', ...]

# Get platforms by category
code_platforms = registry.get_by_category("code", config)
```

### Orchestrator

```python
from sherlockml.enum.orchestrator import Orchestrator

orchestrator = Orchestrator(config)

# Basic search
results = await orchestrator.search(
    usernames=["johndoe", "john_doe"],
    platforms=platforms,
)

# With callback
def on_result(result):
    if result.exists:
        print(f"Found: {result.platform}")

results = await orchestrator.search(
    usernames=["johndoe"],
    platforms=platforms,
    callback=on_result,
)

# Fast-fail on flag
results = await orchestrator.search(
    usernames=["johndoe"],
    platforms=platforms,
    fast_fail=True,
    flag_patterns=[r'flag\{[^}]+\}'],
)

# With timeout
results = await orchestrator.search(
    usernames=["johndoe"],
    platforms=platforms,
    max_time=60.0,  # seconds
)
```

### SearchResults

```python
results = await orchestrator.search(usernames, platforms)

# Summary
print(results.found_count)      # Number of profiles found
print(results.total_platforms)  # Platforms checked
print(results.elapsed_time)     # Search duration
print(results.flags_found)      # List of detected flags

# Iterate results
for result in results.results:
    print(result.platform)      # Platform name
    print(result.username)      # Searched username
    print(result.exists)        # Profile exists?
    print(result.url)           # Profile URL
    print(result.metadata)      # Additional data (may include low_confidence, redirect_detected, etc.)
    print(result.confidence)    # 0.0-1.0 (results with low_confidence=True in metadata scored 0.5-0.55)
    print(result.response_time) # Request time
    print(result.error)         # Error if any
```

---

## Machine Learning

### RAGPipeline

```python
from sherlockml.ml.rag_pipeline import RAGPipeline

# Initialize
rag = RAGPipeline(config.ml.vectorstore_dir)

# Check count
print(f"Documents indexed: {rag.count}")

# Index a single document
doc_id = rag.index(
    content="User bio text...",
    metadata={"platform": "github", "username": "johndoe"},
)

# Index in batch
from sherlockml.ml.rag_pipeline import RAGDocument
documents = [
    RAGDocument(content="User bio text...", metadata={"platform": "github"}),
    RAGDocument(content="Tweet content...", metadata={"platform": "twitter"}),
]
rag.index_batch(documents)

# Query
results = rag.query(
    question="find email addresses",
    top_k=10,
    threshold=0.7,
)

for result in results:
    print(f"Score: {result.score:.2f}")
    print(f"Content: {result.content[:100]}")
    print(f"Metadata: {result.metadata}")

# Get documents by platform
github_docs = rag.get_by_platform("github")

# Export/import
rag.export_to_json(Path("backup.json"))
rag.import_from_json(Path("backup.json"))

# Clear database
rag.clear()
```

### RLController

```python
from sherlockml.ml.rl_controller import RLController

# Initialize (context manager for SQLite)
with RLController(config.ml.rl_weights_path) as rl:
    # Select platforms using Thompson Sampling
    selected = rl.select_platforms(
        available=["github", "twitter", "reddit"],
        n=2,
        use_thompson=True,
    )
    # ['github', 'reddit'] (based on learned weights)

    # Update after result
    rl.update(
        platform="github",
        flag_found=True,
        response_time=0.5,
    )

    # Get stats for a platform
    stats = rl.get_stats("github")
    print(f"Success rate: {stats.success_rate}")

    # Export weights
    weights = rl.export_weights()
    # {'github': 0.87, 'twitter': 0.65, 'reddit': 0.72}

    # Train on dataset
    train_stats = rl.train("ctf_data.json", epochs=50)
    print(f"Trained on {train_stats['entries']} challenges")
```

### NERExtractor

```python
from sherlockml.ml.ner_extractor import NERExtractor

ner = NERExtractor()

# Full extraction
entities = ner.extract("""
Found a flag: flag{s3cr3t_fl4g}
Contact: admin@example.com
Hash: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
Server: 192.168.1.1
""")

print(entities.flags)     # ['flag{s3cr3t_fl4g}']
print(entities.emails)    # ['admin@example.com']
print(entities.hashes)    # ['a94a8fe5ccb19ba61c4c0873d391e987982fbbd3']
print(entities.ips)       # ['192.168.1.1']
print(entities.urls)      # []
print(entities.usernames) # []

# Convert to dict
data = entities.to_dict()

# Flag-only extraction
flags = ner.find_flags(text)
```

---

## Data Extractors

### GitHubScanner

```python
from sherlockml.extract.github_scanner import GitHubScanner
import aiohttp

scanner = GitHubScanner(auth_token="ghp_xxx")

async with aiohttp.ClientSession() as session:
    result = await scanner.scan_user(
        username="targetuser",
        session=session,
        commits=True,
        gists=True,
        depth=20,
    )
    
    print(f"Repos: {len(result.repos)}")
    print(f"Commits: {len(result.commits)}")
    print(f"Gists: {len(result.gists)}")
    print(f"Emails: {result.emails_found}")
    print(f"Flags: {result.flags_found}")
    
    # Search code
    code_results = await scanner.search_code("flag{", session)
```

### WaybackIntegration

```python
from sherlockml.extract.wayback import WaybackIntegration
import aiohttp

wayback = WaybackIntegration()

async with aiohttp.ClientSession() as session:
    # Get snapshots
    snapshots = await wayback.get_snapshots(
        url="https://github.com/targetuser",
        session=session,
        from_date="2020",
        limit=50,
    )
    
    for snap in snapshots:
        print(f"{snap.datetime}: {snap.wayback_url}")
    
    # Full analysis
    result = await wayback.analyze_url(
        "https://example.com",
        session,
    )
    print(f"Hidden endpoints: {result.hidden_endpoints}")
    print(f"Robots.txt entries: {result.robots_entries}")
```

### SocialMediaParser

```python
from sherlockml.extract.social_parser import SocialMediaParser

parser = SocialMediaParser()

# Parse profile page
profile = parser.analyze_profile(html_content, url)
print(profile.platform)
print(profile.username)
print(profile.linked_accounts)

# Extract rel="me" links
links = parser.extract_rel_me_links(html_content)

# Detect platform from URL
platform, username = parser.detect_platform("https://github.com/user")

# Build social graph
graph = parser.build_social_graph(profiles)
clusters = parser.find_clusters()
central = parser.get_central_nodes(n=5)

# Export graph
parser.export_dot("social_graph.dot")
parser.export_graphml("social_graph.graphml")
```

---

## Output Formatters

### JSONReporter

```python
from sherlockml.output.json_reporter import JSONReporter

reporter = JSONReporter(pretty_print=True)

# Generate report
report = reporter.generate_report(
    results,
    include_negative=False,
)

# Save to file
reporter.save(report, "results.json")

# Calculate confidence
confidence = reporter.calculate_confidence(single_result, all_results)
```

### MarkdownWriter

```python
from sherlockml.output.markdown_writer import MarkdownWriter

writer = MarkdownWriter()

# Generate writeup
markdown = writer.generate_writeup(
    results,
    flags=["flag{found_it}"],
    additional_context={"challenge": "OSINT 101"},
)

# Save
writer.save(markdown, "writeup.md")

# Quick summary
summary = writer.generate_quick_summary(results)
# "Found 5 profiles for 'johndoe' across 10 platforms in 15.2s. Flags: 1"
```

### GraphvizExporter

```python
from sherlockml.output.graphviz_export import GraphvizExporter

exporter = GraphvizExporter()

# Export full graph
dot = exporter.export(graph, "network.dot", title="Social Network")

# Export subgraph around node
dot = exporter.export_subgraph(graph, "github:johndoe", depth=2, output="subgraph.dot")

# Render to image (requires graphviz installed)
success = exporter.render_to_image("network.dot", "network.png", format="png")
```

---

## Custom Platforms

### Creating a Platform

```python
from sherlockml.enum.platform_base import BasePlatform, PlatformResult, PlatformCategory

class MyPlatform(BasePlatform):
    name = "myplatform"
    display_name = "My Platform"
    base_url = "https://myplatform.com"
    url_template = "https://myplatform.com/u/{username}"
    category = PlatformCategory.OTHER
    rate_limit_rpm = 30.0  # requests per minute

    def validate_username(self, username: str) -> bool:
        return len(username) >= 3 and username.isalnum()

    async def check_username(self, username: str, session) -> PlatformResult:
        url = self.get_url(username)

        async with session.get(url) as resp:
            exists = resp.status == 200
            metadata = {}

            if exists:
                data = await resp.json()
                metadata = {"bio": data.get("bio")}

            return PlatformResult(
                exists=exists,
                url=url if exists else None,
                metadata=metadata,
            )
```

### Registering

Place in `~/.sherlockml/plugins/my_platform.py` for auto-discovery.
