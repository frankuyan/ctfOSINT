# Docker Deployment Guide

Complete guide for deploying SherlockML with Docker.

## Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/sherlockml.git
cd sherlockml

# Configure environment
cp docker/.env.example .env
# Edit .env with your API tokens

# Start services
docker-compose up -d

# Run searches
docker-compose exec sherlockml sherlockml search targetuser
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ sherlockml  │  │   chromadb  │  │     tor     │         │
│  │  (app)      │──│  (vectors)  │  │   (proxy)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                                   │               │
│         └───────────────┬───────────────────┘               │
│                         │                                   │
│                   sherlockml_net                            │
├─────────────────────────────────────────────────────────────┤
│  Volumes:                                                   │
│  - sherlockml_data: /data                                   │
│  - chromadb_data: /chroma/chroma                           │
│  - ./results: /app/results                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Services

### Main Application (sherlockml)

```yaml
services:
  sherlockml:
    build: .
    image: sherlockml:latest
    entrypoint: ["tail", "-f", "/dev/null"]
    volumes:
      - sherlockml_data:/data
      - ./docker/config.default.yaml:/config/config.yaml:ro
      - ./results:/app/results
```

**Ports:** None exposed (exec-only)  
**Volumes:** 
- `/data` - RL weights, vectorstore, logs
- `/config` - Configuration file
- `/app/results` - Search results

### ChromaDB Vector Store

```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma
```

**Port:** 8000 (HTTP API)  
**Persistence:** chromadb_data volume

### Tor Proxy

```yaml
services:
  tor:
    image: dperson/torproxy:latest
    ports:
      - "9050:9050"
      - "9051:9051"
```

**Ports:**
- 9050: SOCKS5 proxy
- 9051: Control port (identity rotation)

### Optional: Qdrant

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    profiles:
      - qdrant
```

Start with: `docker-compose --profile qdrant up -d`

### Optional: Redis Cache

```yaml
services:
  redis:
    image: redis:7-alpine
    profiles:
      - cache
```

Start with: `docker-compose --profile cache up -d`

---

## Configuration

### Environment Variables

Create `.env` from template:

```bash
cp docker/.env.example .env
```

Edit `.env`:

```bash
# Required for best results
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Optional
TWITTER_BEARER_TOKEN=
TOR_ENABLED=false
```

### Config File

Mount custom config:

```yaml
volumes:
  - ./my-config.yaml:/config/config.yaml:ro
```

Or edit `docker/config.default.yaml`.

---

## Usage

### Running Commands

```bash
# Search
docker-compose exec sherlockml sherlockml search targetuser

# Generate variants
docker-compose exec sherlockml sherlockml generate-variants johndoe --leet

# GitHub scan
docker-compose exec sherlockml sherlockml scan-github targetuser --commits

# RAG query
docker-compose exec sherlockml sherlockml rag-query "find emails"
```

### Interactive Shell

```bash
docker-compose exec sherlockml bash
sherlockml search targetuser
```

### View Logs

```bash
# All services
docker-compose logs -f

# SherlockML only
docker-compose logs -f sherlockml
```

### Access Results

Results are saved to `./results/`:

```bash
ls -la results/
# sherlockml_targetuser.json
# sherlockml_targetuser.md
```

---

## Production Deployment

### Resource Limits

```yaml
services:
  sherlockml:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Health Checks

All services include health checks:

```yaml
healthcheck:
  test: ["CMD", "sherlockml", "--version"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Restart Policies

```yaml
services:
  sherlockml:
    restart: unless-stopped
```

### Logging

```yaml
services:
  sherlockml:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Multi-Host Setup

### Separate Vector DB (Coming Soon)

*Support for remote ChromaDB connections is currently in development.*

### External Tor

```yaml
services:
  sherlockml:
    environment:
      - TOR_HOST=tor.internal
      - TOR_PORT=9050
```

**Note:** You must also update your `config.yaml` to use these variables:

```yaml
proxy:
  host: ${TOR_HOST}
  port: ${TOR_PORT}
```

---

## Building

### Build Image

```bash
docker build -t sherlockml:latest .
```

### Multi-Platform Build

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t sherlockml:latest .
```

### Tagged Release

```bash
docker build -t sherlockml:1.0.0 -t sherlockml:latest .
```

---

## Kubernetes (Helm)

Coming soon: Helm chart for Kubernetes deployment.

For now, use Docker Compose or convert with Kompose:

```bash
kompose convert -f docker-compose.yaml
kubectl apply -f .
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs sherlockml

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Permission Issues

```bash
# Fix volume permissions
sudo chown -R 1000:1000 ./results
```

### Network Issues

```bash
# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

### Tor Not Connecting

```bash
# Check Tor status
docker-compose exec tor curl --socks5 localhost:9050 https://check.torproject.org/
```
