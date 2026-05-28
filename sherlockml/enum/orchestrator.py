"""Async orchestrator for concurrent platform searches."""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

import aiohttp
from aiohttp_socks import ProxyConnector

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sherlockml.config import Config
    from sherlockml.enum.platform_base import BasePlatform, PlatformResult


# Per-platform URL patterns for cross-platform discovery.  Each pattern uses
# a left-boundary look-behind so look-alike domains (notgithub.com) don't
# match, and captures the username portion in group 1.
_SOCIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in (
        # Code hosting
        r'(?<![\w.-])github\.com/([a-zA-Z0-9][a-zA-Z0-9-]{0,38})',
        r'(?<![\w.-])gitlab\.com/([a-zA-Z0-9][a-zA-Z0-9_.-]{1,254})',
        r'(?<![\w.-])bitbucket\.org/([a-zA-Z0-9_-]{1,30})',
        r'(?<![\w.-])keybase\.io/([a-zA-Z0-9_]{2,16})',
        # Mainstream social
        r'(?<![\w.-])(?:twitter|x)\.com/@?([a-zA-Z0-9_]{1,15})',
        r'(?<![\w.-])instagram\.com/([a-zA-Z0-9_.]{1,30})',
        r'(?<![\w.-])linkedin\.com/in/([a-zA-Z0-9-]{3,100})',
        r'(?<![\w.-])reddit\.com/(?:u|user)/([a-zA-Z0-9_-]{3,20})',
        r'(?<![\w.-])(?:www\.)?tiktok\.com/@([a-zA-Z0-9_.]{2,24})',
        r'(?<![\w.-])threads\.net/@([a-zA-Z0-9_.]{1,30})',
        r'(?<![\w.-])(?:[a-z]{2}\.)?pinterest\.com/([a-zA-Z0-9_]{3,30})',
        # Video & streaming
        r'(?<![\w.-])youtube\.com/(?:@|c/|user/)([a-zA-Z0-9_-]{2,30})',
        r'(?<![\w.-])twitch\.tv/([a-zA-Z0-9_]{2,25})',
        r'(?<![\w.-])vimeo\.com/([a-zA-Z0-9-]{3,32})',
        # Writing / Q&A
        r'(?<![\w.-])dev\.to/([a-zA-Z0-9_]{1,30})',
        r'(?<![\w.-])medium\.com/@([a-zA-Z0-9_.-]{2,30})',
        r'(?<![\w.-])stackoverflow\.com/users/\d+/([a-zA-Z0-9_-]{2,30})',
        r'(?<![\w.-])lobste\.rs/~([a-zA-Z0-9_-]{2,30})',
        r'(?<![\w.-])news\.ycombinator\.com/user\?id=([a-zA-Z0-9_-]{2,30})',
        # Messaging
        r'(?<![\w.-])(?:t|telegram)\.me/([a-zA-Z][a-zA-Z0-9_]{4,31})',
        # Audio
        r'(?<![\w.-])soundcloud\.com/([a-zA-Z0-9_-]{3,25})',
        # Gaming
        r'(?<![\w.-])steamcommunity\.com/id/([a-zA-Z0-9_-]{3,32})',
        # Blogging
        r'(?<![\w.-])tumblr\.com/([a-zA-Z0-9-]{3,32})',
        r'(?<![\w.-])([a-zA-Z0-9][a-zA-Z0-9-]{1,31})\.tumblr\.com\b',
        # Fediverse / Mastodon
        r'(?<![\w.-])bsky\.app/profile/([a-zA-Z0-9.-]{2,40})',
        r'(?<![\w.-])mastodon\.(?:social|online|world|cloud)/@([a-zA-Z0-9_]{1,30})',
        r'(?<![\w.-])(?:mas\.to|infosec\.exchange|fosstodon\.org|mstdn\.social|hachyderm\.io|tech\.lgbt|techhub\.social)/@([a-zA-Z0-9_]{1,30})',
    )
]

# Path segments that should never be treated as a username when extracted
# from a discovered URL.  Expanded from the previous short list.
_SKIP_USERNAMES: frozenset[str] = frozenset({
    # Generic site paths
    "about", "help", "login", "signup", "settings", "privacy", "terms",
    "search", "explore", "status", "api", "docs", "blog", "home",
    "tos", "feed", "tags", "trending", "legal", "contact", "press",
    "careers", "pricing", "download", "popular", "new", "top", "all",
    "discover", "directory", "category", "categories", "tag", "topics",
    "topic", "channel", "channels", "watch", "live", "shorts", "static",
    "assets", "images", "img", "css", "js",
    # Subdomain / platform-specific noise added with the wider pattern set
    "www", "staff", "dashboard", "tagged", "register", "auth",
    "ondemand", "features", "stock", "enterprise",
    "premium", "tv", "music", "discover-creators", "discover-channels",
    "trending-topics", "for-you", "foryou", "following",
})


# Email addresses extracted from profile pages.  Standard local@domain.tld
# shape with conservative bounds; the TLD must be 2-24 letters to reject
# accidental matches in code snippets like `obj.foo`.
_EMAIL_RE: re.Pattern[str] = re.compile(
    r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,24})\b',
    re.IGNORECASE,
)

# Bare @handle mentions in bios.  Reject anything preceded by '@', a word
# char, '/' or '.' so we skip mastodon-style `@user@host` (second handle),
# email locals (alice@gmail.com), URL paths (foo/@alice) and decimals.
_HANDLE_RE: re.Pattern[str] = re.compile(
    r'(?<![@\w/.])@([a-zA-Z][a-zA-Z0-9_]{2,29})\b',
)

# Email locals that almost never represent a real person.
_NOISY_EMAIL_LOCALS: frozenset[str] = frozenset({
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "support", "info", "admin", "webmaster", "postmaster",
    "mailer-daemon", "hello", "contact", "abuse", "help",
})


@dataclass
class SearchResult:
    """Result for a single username on a single platform."""
    username: str
    platform: str
    exists: bool
    url: str | None = None
    confidence: float = 0.0
    response_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class SearchResults:
    """Aggregated results from searching multiple platforms."""
    query_username: str
    variants_searched: list[str] = field(default_factory=list)
    results: list[SearchResult] = field(default_factory=list)
    total_platforms: int = 0
    successful_checks: int = 0
    found_count: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_time: float = 0.0
    flags_found: list[str] = field(default_factory=list)
    contacts: list[str] = field(default_factory=list)

    @property
    def found_results(self) -> list[SearchResult]:
        """Get only results where username exists."""
        return [r for r in self.results if r.exists]
    
    @property
    def success_rate(self) -> float:
        """Calculate successful check rate."""
        if self.total_platforms == 0:
            return 0.0
        return self.successful_checks / self.total_platforms
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_username": self.query_username,
            "variants_searched": self.variants_searched,
            "results": [
                {
                    "username": r.username,
                    "platform": r.platform,
                    "exists": r.exists,
                    "url": r.url,
                    "confidence": r.confidence,
                    "response_time": r.response_time,
                    "metadata": r.metadata,
                    "error": r.error,
                }
                for r in self.results
            ],
            "summary": {
                "total_platforms": self.total_platforms,
                "successful_checks": self.successful_checks,
                "found_count": self.found_count,
                "errors_count": len(self.errors),
                "elapsed_time": self.elapsed_time,
            },
            "flags_found": self.flags_found,
            "contacts": self.contacts,
        }


class Orchestrator:
    """Manages concurrent platform searches with rate limiting.
    
    Features:
    - Semaphore-controlled parallelism
    - Per-platform rate limiting
    - Rotating user agents
    - Proxy support (SOCKS5, Tor)
    - Progress callbacks
    - Timeout handling
    
    Example:
        >>> orchestrator = Orchestrator(config)
        >>> results = await orchestrator.search(
        ...     usernames=["john_doe", "johndoe"],
        ...     platforms=registry.get_enabled(config),
        ...     callback=progress_callback,
        ... )
    """
    
    def __init__(
        self,
        config: "Config",
        max_concurrent: int | None = None,
        timeout: float | None = None,
    ):
        """Initialize the orchestrator.
        
        Args:
            config: Application configuration
            max_concurrent: Max concurrent requests (default from config)
            timeout: Request timeout in seconds (default from config)
        """
        self.config = config
        self.max_concurrent = max_concurrent or config.search.max_concurrent
        self.timeout = timeout or config.search.request_timeout
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Rate limiting state per platform
        self._last_request: dict[str, float] = {}
        self._rate_limiters: dict[str, asyncio.Lock] = {}
    
    def _get_user_agent(self) -> str:
        """Get a random user agent from config."""
        return random.choice(self.config.search.user_agents)
    
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create an aiohttp session with optional proxy."""
        connector = None
        
        if self.config.proxy.enabled:
            connector = ProxyConnector.from_url(self.config.proxy.url)
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        default_headers = {"User-Agent": self._get_user_agent()}

        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=default_headers,
        )
    
    async def _rate_limit(self, platform_name: str, rate_limit: float) -> None:
        """Apply rate limiting for a platform.
        
        Args:
            platform_name: Name of the platform
            rate_limit: Requests per second limit
        """
        if platform_name not in self._rate_limiters:
            self._rate_limiters[platform_name] = asyncio.Lock()
        
        async with self._rate_limiters[platform_name]:
            min_interval = 1.0 / rate_limit
            last = self._last_request.get(platform_name, 0)
            elapsed = time.monotonic() - last
            
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            
            self._last_request[platform_name] = time.monotonic()
    
    async def _check_single(
        self,
        username: str,
        platform: "BasePlatform",
        session: aiohttp.ClientSession,
    ) -> SearchResult:
        """Check a single username on a single platform.
        
        Args:
            username: Username to check
            platform: Platform to check on
            session: aiohttp session
            
        Returns:
            SearchResult for this check
        """
        async with self.semaphore:
            platform_config = self.config.get_platform(platform.name)
            rate_limit = platform_config.rate_limit or platform.rate_limit_rps
            max_attempts = self.config.search.retry_attempts + 1
            retry_delay = self.config.search.retry_delay

            for attempt in range(max_attempts):
                await self._rate_limit(platform.name, rate_limit)

                try:
                    result: PlatformResult = await platform.check_username(username, session)

                    metadata = dict(result.metadata)
                    if result.raw_response:
                        metadata["_raw_response"] = result.raw_response

                    confidence = result.confidence
                    exists = result.exists

                    # Lower confidence for borderline positive results
                    if exists and result.raw_response:
                        confidence = self._adjust_confidence(
                            confidence, result.raw_response, username, metadata,
                        )

                    return SearchResult(
                        username=username,
                        platform=platform.name,
                        exists=exists,
                        url=result.url,
                        confidence=confidence,
                        response_time=result.response_time,
                        metadata=metadata,
                        error=result.error,
                    )

                except asyncio.TimeoutError:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return SearchResult(
                        username=username,
                        platform=platform.name,
                        exists=False,
                        error="Request timed out",
                    )

                except Exception as e:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    return SearchResult(
                        username=username,
                        platform=platform.name,
                        exists=False,
                        error=str(e),
                    )

            # Unreachable: the loop always returns within try/except blocks.
            # Defensive fallback kept for type-checker satisfaction.
            raise AssertionError("Unreachable: retry loop did not return")
    
    @staticmethod
    def _adjust_confidence(
        confidence: float,
        body: str,
        username: str,
        metadata: dict[str, Any],
    ) -> float:
        """Lower confidence for borderline positive results.

        Checks whether the response body looks like a real profile page.
        If the body is very short or lacks typical profile indicators,
        the confidence is reduced and the result is tagged.
        """
        # Strip HTML to get plain text length
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text).strip()

        has_image = bool(re.search(r"<img\s", body, re.IGNORECASE))
        has_username_mention = username.lower() in body.lower()

        penalties = 0
        if len(text) < 800:
            penalties += 1
        if not has_image:
            penalties += 1
        if not has_username_mention:
            penalties += 1

        if penalties >= 2:
            metadata["low_confidence"] = True
            return min(confidence, 0.5 + (0.05 * (3 - penalties)))

        return confidence

    @staticmethod
    def _collect_searchable_text(result: "SearchResult") -> list[str]:
        """Gather every text blob worth scanning on a profile result."""
        texts: list[str] = []
        raw = result.metadata.get("_raw_response", "")
        if raw:
            texts.append(raw)
        if result.url:
            texts.append(result.url)
        for v in result.metadata.values():
            if isinstance(v, str) and len(v) < 500:
                texts.append(v)
        return texts

    @staticmethod
    def _extract_discovered_usernames(result: "SearchResult") -> set[str]:
        """Extract additional usernames from a found profile's metadata.

        Scans raw HTML responses and metadata for two kinds of identifiers:
        social-platform URLs (via ``_SOCIAL_PATTERNS``) and bare ``@handle``
        mentions in bio text (via ``_HANDLE_RE``).  Both are returned as
        candidate seeds for cross-platform discovery.
        """
        found: set[str] = set()
        for text in Orchestrator._collect_searchable_text(result):
            for pattern in _SOCIAL_PATTERNS:
                for m in pattern.finditer(text):
                    candidate = m.group(1).lower()
                    if candidate and candidate not in _SKIP_USERNAMES:
                        found.add(candidate)
            for m in _HANDLE_RE.finditer(text):
                handle = m.group(1).lower()
                if handle not in _SKIP_USERNAMES:
                    found.add(handle)
        return found

    @staticmethod
    def _extract_contacts(result: "SearchResult") -> set[str]:
        """Extract contact emails from a found profile's metadata.

        Emails are evidence, not seeds: they're returned for the final
        report but never fed back into the discovery queue.  Generic
        role addresses (noreply@, support@, ...) are filtered out.
        """
        found: set[str] = set()
        for text in Orchestrator._collect_searchable_text(result):
            for m in _EMAIL_RE.finditer(text):
                email = m.group(1).lower()
                local = email.split("@", 1)[0]
                if local in _NOISY_EMAIL_LOCALS:
                    continue
                found.add(email)
        return found

    async def search(
        self,
        usernames: list[str],
        platforms: list["BasePlatform"],
        callback: Callable[[SearchResult], None] | None = None,
        fast_fail: bool = False,
        flag_patterns: list[str] | None = None,
        max_time: float | None = None,
        discover: bool = False,
        max_discovered: int = 15,
        max_hops: int = 2,
    ) -> SearchResults:
        """Execute parallel searches across platforms.

        Args:
            usernames: List of usernames to search
            platforms: List of platforms to search on
            callback: Optional callback for each result
            fast_fail: Stop after first flag found
            flag_patterns: Regex patterns to detect flags
            max_time: Maximum time in seconds (None for no limit)
            discover: Enable cross-platform discovery (when a profile is
                found, extract linked usernames and search those too)
            max_discovered: Maximum total discovered usernames across all hops
            max_hops: Maximum discovery depth.  Hop 0 = seed usernames the
                caller passed in; hop 1 = usernames found in hop-0 profiles;
                etc.  A profile at hop >= max_hops is not mined further.

        Returns:
            Aggregated SearchResults
        """
        start_time = time.monotonic()
        deadline = start_time + max_time if max_time else None

        if not usernames:
            return SearchResults(query_username="", total_platforms=0)

        results = SearchResults(
            query_username=usernames[0],
            variants_searched=usernames.copy(),
            total_platforms=len(platforms) * len(usernames),
        )

        # Compile flag patterns
        compiled_patterns: list[re.Pattern[str]] = []
        if flag_patterns:
            compiled_patterns = [re.compile(p, re.IGNORECASE) for p in flag_patterns]
        elif self.config.ctf.flag_patterns:
            compiled_patterns = [
                re.compile(p, re.IGNORECASE)
                for p in self.config.ctf.flag_patterns
            ]

        # Track every username already searched (key: lowercased) along with
        # the hop depth it was discovered at.  Seeds are hop 0.
        username_hop: dict[str, int] = {u.lower(): 0 for u in usernames}
        searched_usernames: set[str] = set(username_hop)
        discovered_count = 0

        async with await self._create_session() as session:
            pending: set[asyncio.Task[SearchResult]] = set()

            for username in usernames:
                for platform in platforms:
                    pending.add(asyncio.create_task(
                        self._check_single(username, platform, session)
                    ))

            cancelled_count = 0
            stop = False

            while pending and not stop:
                # Bound the wait by the remaining deadline so a hung task
                # cannot keep us past max_time.
                timeout: float | None = None
                if deadline is not None:
                    timeout = deadline - time.monotonic()
                    if timeout <= 0:
                        break

                done, pending = await asyncio.wait(
                    pending,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if not done:
                    # Deadline elapsed before anything finished.
                    break

                for task in done:
                    try:
                        result = task.result()
                    except asyncio.CancelledError:
                        cancelled_count += 1
                        continue

                    results.results.append(result)

                    if result.error is None:
                        results.successful_checks += 1
                    else:
                        results.errors.append(f"{result.platform}: {result.error}")

                    if result.exists:
                        results.found_count += 1

                        # Email harvest (cheap, always-on; doesn't feed
                        # the discovery queue, only the final report).
                        for email in self._extract_contacts(result):
                            if email not in results.contacts:
                                results.contacts.append(email)

                        # Cross-platform discovery: extract linked usernames
                        # and feed new tasks back into `pending`.  A result
                        # at hop H spawns hop H+1 tasks; we stop mining once
                        # H+1 would exceed max_hops or the global cap is hit.
                        if discover and discovered_count < max_discovered:
                            current_hop = username_hop.get(
                                result.username.lower(), 0
                            )
                            next_hop = current_hop + 1
                            if next_hop <= max_hops:
                                new_usernames = self._extract_discovered_usernames(result)
                                for new_u in new_usernames:
                                    if discovered_count >= max_discovered:
                                        break
                                    key = new_u.lower()
                                    if key in searched_usernames:
                                        continue
                                    searched_usernames.add(key)
                                    username_hop[key] = next_hop
                                    discovered_count += 1
                                    results.variants_searched.append(new_u)
                                    results.total_platforms += len(platforms)
                                    logger.info(
                                        "Discovered username %r (hop %d) from %s, adding to search",
                                        new_u,
                                        next_hop,
                                        result.platform,
                                    )
                                    for platform in platforms:
                                        pending.add(asyncio.create_task(
                                            self._check_single(new_u, platform, session)
                                        ))

                    # Scan for flags in metadata values, URL, and raw response
                    if compiled_patterns:
                        texts_to_scan: list[str] = []
                        if result.url:
                            texts_to_scan.append(result.url)
                        if result.metadata:
                            for field_value in result.metadata.values():
                                if isinstance(field_value, str):
                                    texts_to_scan.append(field_value)
                        for text in texts_to_scan:
                            for pattern in compiled_patterns:
                                matches = pattern.findall(text)
                                results.flags_found.extend(matches)

                    if callback:
                        callback(result)

                    if fast_fail and results.flags_found:
                        stop = True
                        break

            # Cancel anything still outstanding (deadline hit or fast-fail).
            for task in pending:
                if not task.done():
                    task.cancel()
                    cancelled_count += 1
            if cancelled_count:
                logger.info("Cancelled %d outstanding tasks", cancelled_count)
            for task in pending:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

        results.elapsed_time = time.monotonic() - start_time

        # Strip raw responses from metadata unless explicitly requested,
        # to avoid leaking PII/secrets in exported output.
        if not self.config.output.include_raw_responses:
            for r in results.results:
                r.metadata.pop("_raw_response", None)

        return results
    
    async def search_single_platform(
        self,
        username: str,
        platform: "BasePlatform",
    ) -> SearchResult:
        """Search a single username on a single platform.
        
        Convenience method for individual checks.
        
        Args:
            username: Username to search
            platform: Platform to search on
            
        Returns:
            SearchResult
        """
        async with await self._create_session() as session:
            return await self._check_single(username, platform, session)
