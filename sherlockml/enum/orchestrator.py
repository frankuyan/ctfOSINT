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

    async def search(
        self,
        usernames: list[str],
        platforms: list["BasePlatform"],
        callback: Callable[[SearchResult], None] | None = None,
        fast_fail: bool = False,
        flag_patterns: list[str] | None = None,
        max_time: float | None = None,
    ) -> SearchResults:
        """Execute parallel searches across platforms.
        
        Args:
            usernames: List of usernames to search
            platforms: List of platforms to search on
            callback: Optional callback for each result
            fast_fail: Stop after first flag found
            flag_patterns: Regex patterns to detect flags
            max_time: Maximum time in seconds (None for no limit)
            
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
        
        async with await self._create_session() as session:
            # Create all tasks
            tasks: list[asyncio.Task[SearchResult]] = []
            
            for username in usernames:
                for platform in platforms:
                    task = asyncio.create_task(
                        self._check_single(username, platform, session)
                    )
                    tasks.append(task)
            
            # Process as completed
            cancelled_count = 0
            for coro in asyncio.as_completed(tasks):
                # Check deadline before awaiting next result
                if deadline and time.monotonic() > deadline:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                            cancelled_count += 1
                    if cancelled_count:
                        logger.info(
                            "Deadline exceeded, cancelled %d remaining tasks",
                            cancelled_count,
                        )
                    break

                try:
                    result = await coro
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

                # Callback
                if callback:
                    callback(result)

                # Fast fail on flag found
                if fast_fail and results.flags_found:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break

            # Await any remaining cancelled tasks to suppress warnings
            for task in tasks:
                if not task.done():
                    try:
                        await task
                    except asyncio.CancelledError:
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
