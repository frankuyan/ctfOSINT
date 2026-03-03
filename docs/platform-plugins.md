# Platform Plugins Guide

SherlockML includes **93 built-in platforms** across 12 categories (including international platforms for Chinese, Russian, Japanese, and Korean services) and supports custom plugins via the plugin system.

## Built-in Platforms

### Code / Developer (22 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **GitHub** | 0.92 | Optional | User API, commits, gists, email extraction |
| **GitHub Gist** | 0.88 | Optional | Gist listing, CTF snippet detection |
| **Keybase** | 0.88 | No | Public keys, social proofs, identity verification |
| **GitLab** | 0.85 | Optional | User API, project search |
| **Pastebin** | 0.85 | No | Profile check, important for CTF flag leaks |
| **Bitbucket** | 0.80 | No | User API, repository listing |
| **Docker Hub** | 0.78 | No | User API, image listing |
| **npm** | 0.75 | No | Package author profiles |
| **PyPI** | 0.75 | No | Python package author profiles |
| **Stack Overflow** | 0.75 | No | Stack Exchange API, reputation |
| **HackerOne** | 0.72 | No | Bug bounty hacker profiles |
| **DEV.to** | 0.70 | No | Developer blog profiles |
| **Codeberg/Gitea** | 0.70 | No | Gitea API, user profiles |
| **RubyGems** | 0.65 | No | Ruby package author profiles |
| **Crates.io** | 0.65 | No | Rust package author profiles |
| **Kaggle** | 0.65 | No | Data science profiles |
| **Hashnode** | 0.60 | No | Developer blog profiles |
| **CodePen** | 0.60 | No | Front-end developer profiles |
| **LeetCode** | 0.60 | No | Competitive programming profiles |
| **Codeforces** | 0.60 | No | Competitive programming API, ratings |
| **Replit** | 0.55 | No | Online IDE profiles |
| **Gitee** | 0.60 | No | Chinese GitHub, code hosting |
| **CSDN** | 0.55 | No | Chinese developer blog/forum |
| **Habr** | 0.55 | No | Russian developer blog/news |
| **Qiita** | 0.55 | No | Japanese developer blog |
| **Codewars** | 0.55 | No | Coding challenge profiles |
| **HackerRank** | 0.55 | No | Coding challenge profiles |

### CTF / Security (2 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **TryHackMe** | 0.85 | No | CTF platform user profiles |
| **Hack The Box** | 0.85 | No | CTF platform user profiles |

### Social (10 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **Twitter/X** | 0.78 | Optional | Profile check, metadata extraction |
| **Reddit** | 0.70 | No | JSON API, account age, karma |
| **Telegram** | 0.65 | No | Public profile check |
| **LinkedIn** | 0.65 | No | Basic profile check (anti-scraping limits) |
| **Instagram** | 0.60 | No | Profile check, follower count |
| **Bluesky** | 0.60 | No | AT Protocol API, profile data |
| **Discord** | 0.55 | No | User profile lookup |
| **Mastodon** | 0.55 | No | WebFinger lookup, ActivityPub |
| **Threads** | 0.55 | No | Meta Threads profile check |
| **Tumblr** | 0.50 | No | Blog profile check |
| **Snapchat** | 0.50 | No | Public profile check |
| **Imgur** | 0.50 | No | Image hosting user profiles |
| **ASKfm** | 0.40 | No | Q&A profile check |
| **Weibo** | 0.50 | No | Chinese social media |
| **VKontakte** | 0.50 | No | Russian social network |

### Video (7 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **YouTube** | 0.70 | No | Channel profile check |
| **TikTok** | 0.60 | No | User profile check |
| **Twitch** | 0.60 | No | Streamer profile check |
| **Vimeo** | 0.45 | No | Video creator profiles |
| **Dailymotion** | 0.40 | No | Video creator profiles |
| **Bilibili** | 0.50 | No | Chinese video platform (API) |
| **Douyin** | 0.40 | No | TikTok China |

### Creative (13 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **Medium** | 0.65 | No | Blog/writing profiles |
| **Substack** | 0.60 | No | Newsletter profiles |
| **WordPress** | 0.55 | No | Blog profiles |
| **Patreon** | 0.55 | No | Creator page check |
| **Pinterest** | 0.50 | No | Profile check |
| **Dribbble** | 0.50 | No | Design portfolio check |
| **Behance** | 0.50 | No | Creative portfolio check |
| **Buy Me a Coffee** | 0.50 | No | Creator page check |
| **DeviantArt** | 0.45 | No | Art profile check |
| **Wattpad** | 0.40 | No | Writing platform profiles |
| **Newgrounds** | 0.40 | No | Creative community profiles |
| **Note (JP)** | 0.45 | No | Japanese blog/creative platform |
| **Naver Blog** | 0.45 | No | Korean blog platform |

### Music (5 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **SoundCloud** | 0.55 | No | Music creator profiles |
| **Spotify** | 0.55 | No | User profiles |
| **Mixcloud** | 0.40 | No | DJ/music profiles |
| **Last.fm** | 0.45 | No | Music listening profiles |
| **Bandcamp** | 0.45 | No | Music creator/label profiles |

### Gaming (8 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **Steam** | 0.60 | No | Community profile check |
| **Roblox** | 0.50 | No | User search API |
| **Xbox Live** | 0.45 | No | Gamertag profiles |
| **Chess.com** | 0.45 | No | Player API, ratings |
| **Lichess** | 0.45 | No | Player API, game history |
| **osu!** | 0.40 | No | Rhythm game profiles |
| **AniList** | 0.40 | No | Anime/manga tracker profiles |
| **MyAnimeList** | 0.40 | No | Anime tracker profiles |

### Professional (7 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **Trello** | 0.55 | No | Public member API |
| **Product Hunt** | 0.55 | No | Maker profiles |
| **About.me** | 0.50 | No | Personal page check |
| **SlideShare** | 0.50 | No | Presentation profiles |
| **XING** | 0.45 | No | German professional network |
| **Freelancer** | 0.45 | No | Freelance marketplace profiles |
| **Fiverr** | 0.45 | No | Freelance marketplace profiles |

### Forum / News (4 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **HackerNews** | 0.80 | No | Firebase API, submission history, karma |
| **Lobsters** | 0.65 | No | JSON API, karma, about |
| **Quora** | 0.50 | No | Q&A profile check |
| **Zhihu** | 0.45 | No | Chinese Q&A platform |
| **Pikabu** | 0.40 | No | Russian social/forum |
| **Baidu Tieba** | 0.40 | No | Chinese forum |

### Other (2 platforms)

| Platform | Weight | Auth | Features |
|----------|--------|------|----------|
| **Gravatar** | 0.60 | No | Email identity linking |
| **Linktree** | 0.55 | No | Link aggregator profiles |

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
