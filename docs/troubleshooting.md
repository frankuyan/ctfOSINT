# Troubleshooting

Common issues and solutions for SherlockML.

## Installation Issues

### Python Version Error

**Error:** `Python 3.11+ required`

**Solution:**
```bash
# Check version
python --version

# Use pyenv to install 3.11
pyenv install 3.11.0
pyenv local 3.11.0
```

### SpaCy Model Download Fails

**Error:** `Can't find model 'en_core_web_sm'`

**Solution:**
```bash
python -m spacy download en_core_web_sm

# Or manually:
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0.tar.gz
```

### ChromaDB Import Error

**Error:** `No module named 'chromadb'`

**Solution:**
```bash
pip install chromadb>=0.4.0
```

### Sentence Transformers CUDA Error

**Error:** `CUDA out of memory`

**Solution:**
```python
# Force CPU usage
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
```

---

## Runtime Issues

### Config File Not Found

**Error:** `Config file not found: ~/.sherlockml/config.yaml`

**Solution:**
```bash
sherlockml init
```

### Invalid Config Format

**Error:** `YAML parse error`

**Solution:**
1. Validate YAML syntax: https://yaml-online-parser.appspot.com/
2. Check for tab characters (use spaces)
3. Ensure proper indentation

### Rate Limit Exceeded

**Error:** `HTTP 429 Too Many Requests`

**Solution:**
```yaml
# config.yaml
search:
  default_rate_limit: 2.0
  max_concurrent: 3
```

Or wait and retry with:
```bash
sherlockml search target --rate-limit 1
```

### Timeout Errors

**Error:** `Request timed out`

**Solution:**
```yaml
search:
  request_timeout: 30  # Increase timeout
```

Or per-search:
```bash
sherlockml search target --max-time 180
```

### Proxy Connection Failed

**Error:** `SOCKS5 connection refused`

**Solution:**
1. Check Tor is running:
   ```bash
   docker-compose ps tor
   ```
2. Verify port:
   ```bash
   curl --socks5 127.0.0.1:9050 https://check.torproject.org/
   ```
3. Check config:
   ```yaml
   proxy:
     host: 127.0.0.1  # or 'tor' in Docker
     port: 9050
   ```

---

## Platform-Specific Issues

### GitHub: 401 Unauthorized

**Cause:** Invalid or expired token

**Solution:**
1. Generate new token: https://github.com/settings/tokens
2. Update config or environment:
   ```bash
   export GITHUB_TOKEN=ghp_newtoken
   ```

### GitHub: 403 Rate Limited

**Cause:** Exceeded API limits

**Solution:**
- With token: 5000 requests/hour
- Without token: 60 requests/hour

Use a token:
```yaml
platforms:
  github:
    auth_token: ${GITHUB_TOKEN}
```

### Twitter: No Results

**Cause:** API restrictions on profile access

**Solution:**
- Twitter heavily restricts scraping
- Results may be limited without API access
- Consider using `--variants` to find alternative handles

### LinkedIn: Always Fails

**Cause:** Aggressive anti-scraping measures

**Solution:**
- LinkedIn actively blocks automation
- Lower rate limit significantly:
  ```yaml
  platforms:
    linkedin:
      rate_limit: 1.0
  ```
- Consider disabling if unreliable:
  ```yaml
  platforms:
    linkedin:
      enabled: false
  ```

---

## Docker Issues

### Container Exits Immediately

**Cause:** Missing entrypoint override

**Solution:**
```yaml
# docker-compose.yaml
services:
  sherlockml:
    entrypoint: ["tail", "-f", "/dev/null"]
```

### Volume Permission Denied

**Cause:** Container runs as non-root user

**Solution:**
```bash
# Fix permissions
sudo chown -R 1000:1000 ./results
```

### Cannot Connect to ChromaDB

**Cause:** Service not ready or network issue

**Solution:**
```bash
# Wait for ChromaDB
docker-compose up -d chromadb
sleep 10
docker-compose up -d sherlockml

# Check health
docker-compose ps
```

### Out of Disk Space

**Cause:** Large vectorstore or logs

**Solution:**
```bash
# Clear logs
docker-compose logs --tail 0

# Clear volumes (WARNING: deletes data)
docker-compose down -v
```

### Docker Credential Helper Error (Colima/macOS)

**Error:** `error getting credentials - err: exec: "docker-credential-osxkeychain": executable file not found in $PATH`

**Cause:** Docker config references osxkeychain credential helper, but it's not available (common with Colima)

**Solution:**
```bash
# Edit ~/.docker/config.json and change:
# "credsStore": "osxkeychain"
# to:
# "credsStore": ""

# Or run:
sed -i '' 's/"credsStore": "osxkeychain"/"credsStore": ""/' ~/.docker/config.json
```

---

## ML Component Issues

### Vectorstore Corrupted

**Error:** `ChromaDB: collection is closed`

**Solution:**
```bash
# Clear and rebuild
rm -rf ~/.sherlockml/vectorstore
sherlockml search target  # Will recreate
```

### RL Weights Not Updating

**Cause:** Database locked or corrupted

**Solution:**
```bash
rm ~/.sherlockml/rl_weights.db
# Weights reset to default
```

### NER Not Finding Entities

**Cause:** SpaCy model not loaded

**Solution:**
```python
# Test SpaCy
import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp("Apple is looking at buying U.K. startup.")
print([(ent.text, ent.label_) for ent in doc.ents])
```

---

## Performance Issues

### Slow Search

**Causes and solutions:**

1. **Too many platforms:** Disable unused platforms
2. **Low rate limit:** Increase if allowed
3. **Many variants:** Use `--max` to limit
4. **Network issues:** Check connection, try proxy

### High Memory Usage

**Cause:** Embedding model loaded multiple times

**Solution:**
```python
# Reuse RAG pipeline instance
rag = RAGPipeline(path)  # Create once, reuse
```

### Vectorstore Query Slow

**Cause:** Large vectorstore without index

**Solution:**
- Use Qdrant for large datasets (>100k documents)
- Consider clearing old data periodically

---

## Debugging

### Enable Verbose Output

```bash
sherlockml -v search target
```

### Check Configuration

```python
from sherlockml.config import load_config
config = load_config()
print(config.model_dump())
```

### Test Individual Platform

```python
import asyncio
import aiohttp
from sherlockml.platforms.github import GitHubPlatform

async def test():
    platform = GitHubPlatform()
    async with aiohttp.ClientSession() as session:
        result = await platform.check("octocat", session)
        print(result)

asyncio.run(test())
```

### View Logs

```bash
# Docker
docker-compose logs -f sherlockml

# Local
tail -f ~/.sherlockml/sherlockml.log
```

---

## Getting Help

### Check Documentation

```bash
sherlockml --help
sherlockml search --help
```

### Report Issues

When reporting bugs, include:

1. SherlockML version: `sherlockml --version`
2. Python version: `python --version`
3. OS: e.g., macOS 14.1, Ubuntu 22.04
4. Full error message
5. Steps to reproduce
6. Configuration (redact tokens)
