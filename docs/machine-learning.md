# Machine Learning Components

SherlockML integrates three ML components for intelligent OSINT.

## Overview

| Component | Purpose | Technology |
|-----------|---------|------------|
| **RAG Pipeline** | Semantic search over indexed data | ChromaDB + Sentence Transformers |
| **RL Controller** | Platform prioritization | Thompson Sampling Multi-Armed Bandit |
| **NER Extractor** | Entity extraction | SpaCy + Custom Regex |

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
               ┌─────────────┴─────────────┐
               │                           │
      ┌────────▼────────┐        ┌────────▼────────┐
      │    ChromaDB     │   OR   │     Qdrant      │
      │ (Local/Server)  │        │    (Server)     │
      └─────────────────┘        └─────────────────┘
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
from sherlockml.ml import RAGPipeline

rag = RAGPipeline("~/.sherlockml/vectorstore")

# Index documents
documents = [
    {"content": "Found email: target@example.com", "source": "github"},
    {"content": "User bio: CTF player since 2020", "source": "twitter"},
]
rag.index(documents)
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
  
  # Vectorstore backend
  vectorstore_type: chromadb  # or qdrant
  vectorstore_path: ~/.sherlockml/vectorstore
  
  # Minimum similarity for results
  rag_threshold: 0.75
  
  # ChromaDB server mode (optional)
  chromadb_host: localhost
  chromadb_port: 8000
```

### ChromaDB vs Qdrant

| Feature | ChromaDB | Qdrant |
|---------|----------|--------|
| Setup | Embedded/simple | Server required |
| Scalability | Single machine | Distributed |
| Persistence | SQLite | Custom format |
| Best For | Local/dev | Production/team |

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
from sherlockml.ml import RLController

rl = RLController("~/.sherlockml/rl_weights.db")
weights = rl.export_weights()
print(weights)
# {'github': 0.87, 'pastebin': 0.92, 'twitter': 0.45, ...}
```

### Configuration

```yaml
ml:
  rl_learning_rate: 0.1      # Weight update rate
  rl_exploration_rate: 0.15  # Random exploration probability
  rl_weights_db: ~/.sherlockml/rl_weights.db
```

### CTF-Specific Training

For CTF competitions, train on past challenges:

```python
# Load past CTF challenge results
training_data = load_ctf_archive("picoctf_2023.json")

rl = RLController()
stats = rl.train(training_data, epochs=50)
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
from sherlockml.ml import NERExtractor

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

### Custom Patterns

Add custom patterns via configuration:

```yaml
# ~/.sherlockml/ner_patterns.yaml
patterns:
  - name: CUSTOM_FLAG
    pattern: 'MYCTF_[A-Za-z0-9_]+'
    type: flag
    
  - name: INTERNAL_IP
    pattern: '10\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    type: ip
```

### SpaCy Integration

For general NER (people, organizations):

```python
entities = ner.extract(text)
print(entities.locations)   # Extracted with SpaCy
print(entities.organizations)
```

### Configuration

```yaml
ml:
  ner_model: en_core_web_sm  # SpaCy model
  custom_patterns_file: ~/.sherlockml/ner_patterns.yaml
```

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
| < 10,000 | ChromaDB embedded |
| 10,000 - 100,000 | ChromaDB server |
| > 100,000 | Qdrant cluster |

### GPU Acceleration

```python
# Enable GPU for embeddings (if available)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
```
