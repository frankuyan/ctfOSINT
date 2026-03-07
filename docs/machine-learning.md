# Machine Learning Components

SherlockML integrates four ML components for intelligent OSINT.

## Overview

| Component | Purpose | Technology |
|-----------|---------|------------|
| **LLM Verification** | Verifying if profiles are real/active | Large Language Models (OpenAI/Anthropic/Gemini) |
| **RAG Pipeline** | Semantic search over indexed data | ChromaDB + Sentence Transformers |
| **RL Controller** | Platform prioritization | Thompson Sampling Multi-Armed Bandit |
| **NER Extractor** | Entity extraction | SpaCy + Custom Regex |

---

## LLM Verification

### What is LLM Verification?

Because modern platforms often use Single Page Applications (SPAs) or have complex bot-protection mechanisms, simply checking for a 200 OK status or performing basic regex checks can lead to false positives (e.g., hitting a generic "User not found" page) or false negatives.

SherlockML addresses this by sending the raw HTML of discovered profiles to a Large Language Model (LLM) such as OpenAI's GPT-4, Anthropic's Claude, or Google's Gemini, which intelligently determines if the profile is genuine.

### How It Works

1. **Extraction:** Before stripping the page content, SherlockML extracts structural JSON (`application/ld+json` or `application/json`) from `<script>` tags, which is heavily used by SPAs to store profile data.
2. **Text Normalization:** It removes styling and non-relevant scripts, converting structural HTML into a plaintext format with structural hints.
3. **LLM Evaluation:** The extracted structured data and plaintext are sent to the LLM.
4. **OSINT Extraction:** The LLM extracts relevant details from the page — bio, display name, join date, activity level, external links, and other notable info (location, email, interests).
5. **Robust Parsing:** The LLM responds with a JSON verdict (`real`, `empty`, or `suspicious`) along with a confidence score, explanation, and extracted OSINT fields. The result is parsed using a robust regex engine capable of handling nested JSON and markdown fences.

### Output

Verification results are displayed in two separate tables:

- **Verified Profiles** (green border): Real and suspicious accounts shown with full OSINT details — display name, bio, join date, activity summary, external links, and notable info.
- **Empty / Default Pages** (dimmed): Compact list of platforms that returned empty, suspended, or default pages.

For platforms that use JSON APIs internally (e.g., Reddit), SherlockML fetches the profile page separately using browser-like headers (`User-Agent`, `Sec-Fetch-*`, etc.) to avoid being blocked. Any fetch failures are reported rather than silently skipped.

### Usage

You can enable LLM verification by passing the `--verify` flag to the search command:

```bash
sherlockml search targetuser --verify --llm-key sk-...
```

Configuration can also be set within your `config.yaml`:

```yaml
llm:
  enabled: true
  provider: openai
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini
```

---

## RAG Pipeline

### What is RAG?

Retrieval-Augmented Generation (RAG) combines vector search with language models. SherlockML uses the retrieval component to:

1. Index discovered content (profiles, posts, commits)
2. Query indexed data semantically ("find emails mentioning github")
3. Surface relevant information across searches

### Architecture

```
                    ┌─────────────────┐
                    │ Content to Index│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Sentence        │
                    │ Transformer     │
                    │ (all-MiniLM-L6) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Vector Embedding│
                    │ (384 dimensions)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    ChromaDB     │
                    │  (Persistent)   │
                    │ Cosine Similarity│
                    └─────────────────┘
```

### Usage

#### Automatic Indexing

Content is indexed automatically during searches:

```bash
sherlockml search targetuser
# Results are indexed to vectorstore
```

#### Manual Indexing

```python
from sherlockml.ml.rag_pipeline import RAGPipeline

rag = RAGPipeline("~/.sherlockml/vectorstore")

# Index individual documents
rag.index(
    content="Found email: target@example.com",
    metadata={"platform": "github", "username": "target"},
)
rag.index(
    content="User bio: CTF player since 2020",
    metadata={"platform": "twitter", "username": "target"},
)
```

#### Querying

```bash
sherlockml rag-query "emails related to target" --top-k 10
```

```python
results = rag.query("find github profiles", top_k=5, threshold=0.7)
for result in results:
    print(f"{result.score:.2f}: {result.content[:100]}")
```

### Configuration

```yaml
ml:
  # Embedding model (HuggingFace)
  embedding_model: sentence-transformers/all-MiniLM-L6-v2

  # Vectorstore path (persistent ChromaDB)
  vectorstore_path: ~/.sherlockml/vectorstore

  # Minimum similarity for results
  rag_threshold: 0.75
```

---

## RL Controller

### What is RL for OSINT?

Reinforcement Learning optimizes platform search order by:

1. Learning which platforms yield results
2. Balancing exploration (trying new platforms) vs exploitation (using proven ones)
3. Adapting to CTF-specific patterns

### Algorithm: Thompson Sampling

Thompson Sampling is a multi-armed bandit algorithm that:

1. Models each platform's success rate as a Beta distribution
2. Samples from each distribution to get expected values
3. Ranks platforms by sampled values
4. Updates distributions based on outcomes

```
Beta(α, β) where:
  α = successful checks + 1
  β = failed checks + 1

Sample: s ~ Beta(α, β)
Select: top-k platforms by s
```

### Usage

#### Automatic Updates

```bash
sherlockml search targetuser
# RL weights update based on which platforms found results
```

#### Training on Historical Data

```bash
sherlockml rl-train --dataset ctf_archive.json --epochs 100
```

Dataset format:
```json
[
  {
    "challenge": "osint_001",
    "platforms": {
      "github": true,    // Found flag on GitHub
      "twitter": false,  // Checked, no result
      "pastebin": true   // Found flag
    }
  }
]
```

#### Export Weights

```python
from sherlockml.ml.rl_controller import RLController

with RLController("~/.sherlockml/rl_weights.db") as rl:
    weights = rl.export_weights()
    print(weights)
    # {'github': 0.87, 'pastebin': 0.92, 'twitter': 0.45, ...}
```

### Configuration

```yaml
ml:
  rl_learning_rate: 0.1      # Weight update rate (0.0-1.0)
  rl_weights_db: ~/.sherlockml/rl_weights.db
```

### CTF-Specific Training

For CTF competitions, train on past challenges:

```python
from sherlockml.ml.rl_controller import RLController

with RLController("~/.sherlockml/rl_weights.db") as rl:
    stats = rl.train("picoctf_2023.json", epochs=50)
    print(f"Trained on {stats['entries']} challenges")
```

---

## NER Extractor

### What is NER?

Named Entity Recognition (NER) identifies and classifies entities in text:

- **Standard NER**: People, organizations, locations
- **CTF NER**: Flags, hashes, emails, IPs, usernames

### Entity Types

| Entity | Pattern | Example |
|--------|---------|---------|
| FLAG | `(flag\|ctf\|...)\{[^}]+\}` | `flag{s3cr3t}` |
| EMAIL | `[a-zA-Z0-9._%+-]+@...` | `user@example.com` |
| HASH_MD5 | `[a-f0-9]{32}` | `d41d8cd98f00b204e9800998ecf8427e` |
| HASH_SHA1 | `[a-f0-9]{40}` | `da39a3ee5e6b4b0d3255bfef95601890afd80709` |
| HASH_SHA256 | `[a-f0-9]{64}` | `e3b0c44298fc1...` |
| IP | `\\d{1,3}\\.\\d{1,3}...` | `192.168.1.1` |
| URL | `https?://...` | `https://example.com` |
| USERNAME | `@[a-zA-Z0-9_]+` | `@target_user` |

### Usage

#### Extraction

```python
from sherlockml.ml.ner_extractor import NERExtractor

ner = NERExtractor()

text = """
Found a flag: flag{s3cr3t_fl4g_h3r3}
Contact: admin@ctfchallenge.com
Hash: a94a8fe5ccb19ba61c4c0873d391e987982fbbd3
"""

entities = ner.extract(text)
print(entities.flags)   # ['flag{s3cr3t_fl4g_h3r3}']
print(entities.emails)  # ['admin@ctfchallenge.com']
print(entities.hashes)  # ['a94a8fe5ccb19ba61c4c0873d391e987982fbbd3']
```

#### Flag-Only Extraction

```python
flags = ner.find_flags(text)
# ['flag{s3cr3t_fl4g_h3r3}']
```

### SpaCy Integration

For general NER (people, organizations, locations):

```python
entities = ner.extract(text)
print(entities.locations)   # Extracted with SpaCy (GPE, LOC labels)
print(entities.projects)    # Extracted with SpaCy (ORG label)
print(entities.usernames)   # Regex + SpaCy PERSON labels
```

### Configuration

```yaml
ml:
  ner_model_path: ~/.sherlockml/ner_model  # Custom SpaCy model path
```

If no custom model is found, the default `en_core_web_sm` model is used. It will be automatically downloaded if not already installed.

---

## Performance Considerations

### Embedding Model

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| all-MiniLM-L6-v2 | 80MB | Fast | Good |
| all-mpnet-base-v2 | 420MB | Medium | Better |
| paraphrase-multilingual | 1GB | Slow | Best (multilingual) |

### Vectorstore Scaling

| Documents | Recommendation |
|-----------|----------------|
| < 10,000 | ChromaDB persistent (default) |
| 10,000 - 100,000 | ChromaDB persistent |
| > 100,000 | Consider periodic cleanup |

### GPU Acceleration

```python
# Enable GPU for embeddings (if available)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
```
