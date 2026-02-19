# Platform Plugins Guide

SherlockML includes 10 built-in platforms and supports custom plugins via the plugin system.

## Built-in Platforms

### Tier 1: High Reliability (>0.85 weight)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **GitHub** | 0.92 | Optional | User API, commits, gists, email extraction |
| **Keybase** | 0.88 | No | Public keys, social proofs, identity verification |
| **GitLab** | 0.85 | Optional | User API, project search |
| **Pastebin** | 0.85 | No | Profile check, important for CTF flag leaks |

### Tier 2: Medium Reliability (0.65-0.85 weight)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **HackerNews** | 0.80 | No | Firebase API, submission history, karma |
| **Twitter/X** | 0.78 | Optional | Profile check, metadata extraction |
| **Reddit** | 0.70 | No | JSON API, account age, karma |
| **LinkedIn** | 0.65 | No | Basic profile check (anti-scraping limits) |

### Tier 3: Lower Reliability (<0.65 weight)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **Instagram** | 0.60 | No | Profile check, follower count |
| **Mastodon** | 0.55 | No | WebFinger lookup, ActivityPub |

---

## Platform Configuration

### Enabling/Disabling Platforms

```yaml
platforms:
  github:
    enabled: true
  instagram:
    enabled: false  # Too many false positives
```

### Setting Priority Weights

```yaml
platforms:
  pastebin:
    enabled: true
    priority_weight: 0.95  # High priority for CTF
```

### Authentication

```yaml
platforms:
  github:
    auth_token: ${GITHUB_TOKEN}
```

---

## Platform Details

### GitHub

**Endpoint:** `https://api.github.com/users/{username}`

**Features:**
- User profile metadata (bio, location, email, company)
- Public repository count
- Follower/following counts
- Account creation date

**Authentication Benefits:**
- 5000 requests/hour (vs 60 unauthenticated)
- Access to commit search API
- Gist enumeration

**Usage:**
```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
sherlockml search targetuser
sherlockml scan-github targetuser --commits
```

### Twitter/X

**Endpoint:** Profile page scraping (API access limited)

**Features:**
- Profile existence check
- Basic metadata from page content

**Limitations:**
- Rate limiting is aggressive
- API requires elevated access

### Reddit

**Endpoint:** `https://www.reddit.com/user/{username}/about.json`

**Features:**
- Account existence
- Karma (comment + link)
- Account age
- Subreddit activity

### LinkedIn

**Endpoint:** `https://www.linkedin.com/in/{username}`

**Features:**
- Basic profile check

**Limitations:**
- Aggressive anti-scraping
- Conservative rate limiting required

### Keybase

**Endpoint:** `https://keybase.io/_/api/1.0/user/lookup.json?username={username}`

**Features:**
- Full profile data
- Linked social proofs (GitHub, Twitter, etc.)
- PGP keys
- Cryptocurrency addresses

**CTF Value:** High - Often contains cross-platform links

### HackerNews

**Endpoint:** `https://hacker-news.firebaseio.com/v0/user/{username}.json`

**Features:**
- Profile existence
- Karma score
- Account creation
- Submission history

**CTF Value:** High - Tech-focused, often used by CTF players

### Pastebin

**Endpoint:** `https://pastebin.com/u/{username}`

**Features:**
- Profile check
- Public paste count

**CTF Value:** Very High - Common flag leak location

### Mastodon

**Endpoint:** WebFinger at instance

**Features:**
- Federated identity lookup
- Profile metadata

**Note:** Requires instance URL configuration

### GitLab

**Endpoint:** `https://gitlab.com/api/v4/users?username={username}`

**Features:**
- User profile
- Public project count
- Activity

### Instagram

**Endpoint:** Profile page scraping

**Features:**
- Profile existence
- Basic metadata

**Limitations:**
- Aggressive rate limiting
- Requires careful handling

---

## Creating Custom Plugins

### Plugin Location

Place plugins in: `~/.sherlockml/plugins/`

### Basic Plugin Template

```python
"""Custom platform plugin for MyService."""
from sherlockml.enum.platform_base import BasePlatform, PlatformResult, PlatformCategory
import time

class MyServicePlatform(BasePlatform):
    """MyService platform integration."""

    # Required attributes
    name = "myservice"
    display_name = "My Service"
    base_url = "https://myservice.com"
    url_template = "https://myservice.com/users/{username}"
    category = PlatformCategory.OTHER

    # Optional attributes
    rate_limit_rpm = 30.0  # requests per minute

    def validate_username(self, username: str) -> bool:
        """Validate username format for this platform."""
        if len(username) < 3 or len(username) > 20:
            return False
        return username.replace("_", "").isalnum()

    async def check_username(
        self,
        username: str,
        session,
    ) -> PlatformResult:
        """Check if username exists on this platform."""
        if not self.validate_username(username):
            return PlatformResult(exists=False, error="Invalid username format")

        url = self.get_url(username)
        headers = self.get_headers()
        start = time.monotonic()

        try:
            async with session.get(url, headers=headers) as resp:
                response_time = time.monotonic() - start
                exists = resp.status == 200

                metadata = {}
                if exists:
                    data = await resp.json()
                    metadata = {
                        "display_name": data.get("name"),
                        "bio": data.get("bio"),
                        "followers": data.get("followers_count"),
                    }

                return PlatformResult(
                    exists=exists,
                    url=url if exists else None,
                    metadata=metadata,
                    confidence=0.9 if exists else 0.95,
                    response_time=response_time,
                )

        except Exception as e:
            return PlatformResult(
                exists=False,
                error=str(e),
                response_time=time.monotonic() - start,
            )
```

### HTTP Check Helper

For simple HTTP status code-based checks, use the `HTTPCheckPlatform` base class:

```python
from sherlockml.enum.platform_base import HTTPCheckPlatform, PlatformCategory

class SimpleService(HTTPCheckPlatform):
    name = "simpleservice"
    display_name = "Simple Service"
    base_url = "https://simpleservice.com"
    url_template = "https://simpleservice.com/u/{username}"
    category = PlatformCategory.OTHER

    # Check method: "HEAD" (faster) or "GET"
    check_method = "GET"

    # Status codes that indicate user exists
    exists_status_codes = {200}

    # Status codes that indicate user doesn't exist
    not_found_status_codes = {404}
```

This automatically handles requests, timing, and result creation.

### Plugin Discovery

Plugins are auto-discovered on import. File naming:
- `my_platform.py` → Class `MyPlatformPlatform` or `MyPlatform`

### Testing Your Plugin

```python
# test_my_plugin.py
import pytest
import aiohttp
from my_plugin import MyServicePlatform

@pytest.mark.asyncio
async def test_valid_user():
    platform = MyServicePlatform()
    async with aiohttp.ClientSession() as session:
        result = await platform.check_username("known_user", session)
        assert result.exists

@pytest.mark.asyncio
async def test_invalid_user():
    platform = MyServicePlatform()
    async with aiohttp.ClientSession() as session:
        result = await platform.check_username("definitely_not_a_user_12345", session)
        assert not result.exists
```

---

## Platform Priority (RL)

The RL controller learns optimal platform ordering:

```python
# After training
weights = rl.export_weights()
# {'pastebin': 0.92, 'github': 0.88, 'keybase': 0.85, ...}
```

### Training on CTF Data

```bash
sherlockml rl-train --dataset past_ctfs.json --epochs 100
```

### Manual Weight Override

```yaml
platforms:
  pastebin:
    priority_weight: 0.99  # Always check first
```
