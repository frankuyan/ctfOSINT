"""Wayback Machine integration for historical profile analysis."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING
from urllib.parse import urlparse

from sherlockml.flags import compile_flag_patterns, extract_flags

if TYPE_CHECKING:
    import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class WaybackSnapshot:
    """A Wayback Machine snapshot."""
    url: str
    timestamp: str
    original_url: str
    status_code: int
    mime_type: str

    @property
    def datetime(self) -> datetime:
        """Parse timestamp to datetime."""
        return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S")

    @property
    def wayback_url(self) -> str:
        """Get full Wayback Machine URL."""
        return f"https://web.archive.org/web/{self.timestamp}/{self.original_url}"


@dataclass
class WaybackDiff:
    """Difference between two snapshots."""
    old_timestamp: str
    new_timestamp: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)


@dataclass
class WaybackResult:
    """Result from Wayback Machine analysis."""
    original_url: str
    snapshots: list[WaybackSnapshot] = field(default_factory=list)
    hidden_endpoints: list[str] = field(default_factory=list)
    robots_entries: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    historical_content: list[dict[str, Any]] = field(default_factory=list)
    flags_found: list[str] = field(default_factory=list)
    diffs: list[WaybackDiff] = field(default_factory=list)

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)

    @property
    def date_range(self) -> tuple[str, str] | None:
        """Get earliest and latest snapshot dates."""
        if not self.snapshots:
            return None

        dates = sorted([s.timestamp for s in self.snapshots])
        return (dates[0], dates[-1])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data: dict[str, Any] = {
            "original_url": self.original_url,
            "snapshot_count": self.snapshot_count,
            "date_range": self.date_range,
            "snapshots": [
                {
                    "timestamp": s.timestamp,
                    "datetime": s.datetime.isoformat(),
                    "original_url": s.original_url,
                    "wayback_url": s.wayback_url,
                    "status_code": s.status_code,
                    "mime_type": s.mime_type,
                }
                for s in self.snapshots
            ],
            "hidden_endpoints": self.hidden_endpoints,
            "robots_entries": self.robots_entries,
            "sitemap_urls": self.sitemap_urls,
            "flags_found": self.flags_found,
        }
        if self.historical_content:
            data["historical_content"] = self.historical_content
        if self.diffs:
            data["diffs"] = [
                {
                    "old_timestamp": d.old_timestamp,
                    "new_timestamp": d.new_timestamp,
                    "added_lines": d.added_lines[:50],
                    "removed_lines": d.removed_lines[:50],
                }
                for d in self.diffs
            ]
        return data


class WaybackIntegration:
    """Internet Archive CDX API integration.

    Query historical snapshots, extract hidden endpoints from
    robots.txt and sitemap.xml, analyze profile changes over time,
    and scan archived content for CTF flags.

    Example:
        >>> wayback = WaybackIntegration()
        >>> result = await wayback.analyze_url(
        ...     "https://github.com/targetuser",
        ...     session, from_date="2020"
        ... )
        >>> for snapshot in result.snapshots:
        ...     print(f"{snapshot.datetime}: {snapshot.wayback_url}")
    """

    CDX_API = "https://web.archive.org/cdx/search/cdx"
    WAYBACK_BASE = "https://web.archive.org/web"

    def __init__(self, rate_limit: float = 10.0):
        """Initialize Wayback integration.

        Args:
            rate_limit: Requests per minute to Wayback API
        """
        self.rate_limit = rate_limit
        self._last_request = 0.0

    async def _rate_limit_wait(self) -> None:
        """Wait for rate limiting."""
        import time
        min_interval = 60.0 / self.rate_limit
        elapsed = time.monotonic() - self._last_request
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = time.monotonic()

    async def get_snapshots(
        self,
        url: str,
        session: "aiohttp.ClientSession",
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
    ) -> list[WaybackSnapshot]:
        """Query CDX API for historical snapshots.

        Args:
            url: URL to search for
            session: aiohttp session
            from_date: Start date (YYYY or YYYYMMDD)
            to_date: End date (YYYY or YYYYMMDD)
            limit: Maximum number of snapshots

        Returns:
            List of WaybackSnapshot objects
        """
        await self._rate_limit_wait()

        params = {
            "url": url,
            "output": "json",
            "limit": limit,
            "fl": "timestamp,original,statuscode,mimetype",
        }

        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        snapshots: list[WaybackSnapshot] = []

        try:
            async with session.get(self.CDX_API, params=params) as resp:
                if resp.status != 200:
                    return snapshots

                data = await resp.json()

                # First row is headers
                if len(data) > 1:
                    for row in data[1:]:
                        if len(row) >= 4:
                            snapshots.append(WaybackSnapshot(
                                url=f"{self.WAYBACK_BASE}/{row[0]}/{row[1]}",
                                timestamp=row[0],
                                original_url=row[1],
                                status_code=int(row[2]) if row[2].isdigit() else 0,
                                mime_type=row[3],
                            ))

        except Exception as e:
            logger.debug("Failed to get snapshots for %s: %s", url, e)

        return snapshots

    async def analyze_url(
        self,
        url: str,
        session: "aiohttp.ClientSession",
        from_date: str | None = None,
        to_date: str | None = None,
        flag_patterns: list[str] | None = None,
        scan_content: bool = False,
        diff_snapshots: bool = False,
        max_content_snapshots: int = 5,
    ) -> WaybackResult:
        """Full analysis of a URL's historical data.

        Args:
            url: URL to analyze
            session: aiohttp session
            from_date: Start date filter
            to_date: End date filter
            flag_patterns: Regex patterns to scan for CTF flags
            scan_content: Fetch and scan snapshot content for flags
            diff_snapshots: Compare consecutive snapshots for changes
            max_content_snapshots: Max snapshots to fetch content from

        Returns:
            WaybackResult with all findings
        """
        result = WaybackResult(original_url=url)

        # Get snapshots
        result.snapshots = await self.get_snapshots(
            url, session, from_date, to_date
        )

        # Parse domain for robots.txt and sitemap.xml
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Check robots.txt and sitemap.xml in parallel
        robots_task = self.extract_robots_entries(base_url, session)
        sitemap_task = self.extract_sitemap_urls(base_url, session)
        result.robots_entries, result.sitemap_urls = await asyncio.gather(
            robots_task, sitemap_task
        )

        # Find hidden endpoints
        result.hidden_endpoints = self._find_hidden_endpoints(
            result.robots_entries
        )

        # Compile flag patterns
        compiled_flags = self._compile_flag_patterns(flag_patterns)

        # Scan snapshot content for flags and build diffs
        if (scan_content or diff_snapshots) and result.snapshots:
            await self._scan_snapshot_content(
                result, session, compiled_flags,
                scan_content=scan_content,
                diff_snapshots=diff_snapshots,
                max_snapshots=max_content_snapshots,
            )

        # Also scan robots/sitemap for flags
        if compiled_flags:
            for text in result.robots_entries + result.sitemap_urls:
                for flag in extract_flags(text, compiled_flags):
                    if flag not in result.flags_found:
                        result.flags_found.append(flag)

        return result

    async def scan_profile_history(
        self,
        username: str,
        session: "aiohttp.ClientSession",
        platforms: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        flag_patterns: list[str] | None = None,
    ) -> list[WaybackResult]:
        """Scan Wayback Machine for a username's profile across platforms.

        Builds profile URLs for known platforms and checks the archive
        for historical snapshots. Useful for finding deleted profiles,
        old bios, and flags hidden in archived pages.

        Args:
            username: Target username
            session: aiohttp session
            platforms: Platform names to check (default: common set)
            from_date: Start date filter
            to_date: End date filter
            flag_patterns: CTF flag regex patterns

        Returns:
            List of WaybackResult for each platform with snapshots
        """
        platform_urls = self._build_profile_urls(username, platforms)
        compiled_flags = self._compile_flag_patterns(flag_patterns)

        results: list[WaybackResult] = []

        for platform_name, url in platform_urls:
            wr = WaybackResult(original_url=url)
            wr.snapshots = await self.get_snapshots(
                url, session, from_date, to_date, limit=50,
            )

            if not wr.snapshots:
                continue

            # Scan a few snapshots for flags
            if compiled_flags:
                await self._scan_snapshot_content(
                    wr, session, compiled_flags,
                    scan_content=True,
                    diff_snapshots=False,
                    max_snapshots=3,
                )

            results.append(wr)
            logger.info(
                "Found %d snapshots for %s on %s",
                len(wr.snapshots), username, platform_name,
            )

        return results

    async def scan_url_wildcard(
        self,
        domain: str,
        session: "aiohttp.ClientSession",
        from_date: str | None = None,
        to_date: str | None = None,
        flag_patterns: list[str] | None = None,
    ) -> WaybackResult:
        """Wildcard scan: find all archived pages under a domain.

        Uses the CDX API's wildcard matching to discover all URLs
        ever archived for a domain. Great for finding hidden pages,
        leaked files, and forgotten endpoints.

        Args:
            domain: Domain to scan (e.g. "example.com")
            session: aiohttp session
            from_date: Start date filter
            to_date: End date filter
            flag_patterns: CTF flag patterns

        Returns:
            WaybackResult with all discovered URLs
        """
        wildcard_url = f"{domain}/*"
        result = WaybackResult(original_url=domain)

        result.snapshots = await self.get_snapshots(
            wildcard_url, session, from_date, to_date, limit=500,
        )

        # Deduplicate by original URL to find unique pages
        seen_urls: set[str] = set()
        unique_snapshots: list[WaybackSnapshot] = []
        for s in result.snapshots:
            if s.original_url not in seen_urls:
                seen_urls.add(s.original_url)
                unique_snapshots.append(s)

        result.hidden_endpoints = [
            s.original_url for s in unique_snapshots
            if any(kw in s.original_url.lower() for kw in (
                "flag", "secret", "admin", "backup", "config",
                ".env", ".git", "debug", "test", "private",
                ".txt", ".log", ".bak", ".sql", ".key",
            ))
        ]

        # Scan interesting pages for flags
        compiled_flags = self._compile_flag_patterns(flag_patterns)
        if compiled_flags:
            interesting = [
                s for s in unique_snapshots
                if any(kw in s.original_url.lower() for kw in (
                    "flag", "secret", "ctf", ".txt", "key", "hidden",
                ))
            ]
            for snapshot in interesting[:10]:
                content = await self._fetch_snapshot_content(
                    snapshot, session
                )
                if content:
                    for flag in extract_flags(content, compiled_flags):
                        if flag not in result.flags_found:
                            result.flags_found.append(flag)

                    result.historical_content.append({
                        "url": snapshot.original_url,
                        "timestamp": snapshot.timestamp,
                        "excerpt": content[:500],
                    })

        return result

    async def extract_robots_entries(
        self,
        base_url: str,
        session: "aiohttp.ClientSession",
    ) -> list[str]:
        """Extract entries from historical robots.txt."""
        robots_url = f"{base_url}/robots.txt"
        entries: list[str] = []

        snapshots = await self.get_snapshots(robots_url, session, limit=5)

        for snapshot in snapshots[:3]:
            await self._rate_limit_wait()

            try:
                async with session.get(snapshot.wayback_url) as resp:
                    if resp.status == 200:
                        text = await resp.text()

                        for line in text.split("\n"):
                            line = line.strip()
                            if line.startswith(("Disallow:", "Allow:")):
                                path = line.split(":", 1)[1].strip()
                                if path and path not in entries:
                                    entries.append(path)

            except Exception as e:
                logger.debug("Failed to fetch robots.txt snapshot: %s", e)
                continue

        return entries

    async def extract_sitemap_urls(
        self,
        base_url: str,
        session: "aiohttp.ClientSession",
    ) -> list[str]:
        """Extract URLs from historical sitemap.xml."""
        sitemap_url = f"{base_url}/sitemap.xml"
        urls: list[str] = []

        snapshots = await self.get_snapshots(sitemap_url, session, limit=3)

        for snapshot in snapshots[:2]:
            await self._rate_limit_wait()

            try:
                async with session.get(snapshot.wayback_url) as resp:
                    if resp.status == 200:
                        text = await resp.text()

                        url_pattern = re.compile(r'<loc>([^<]+)</loc>')
                        for match in url_pattern.finditer(text):
                            url = match.group(1)
                            if url not in urls:
                                urls.append(url)

            except Exception as e:
                logger.debug("Failed to fetch sitemap snapshot: %s", e)
                continue

        return urls

    def _find_hidden_endpoints(self, robots_entries: list[str]) -> list[str]:
        """Find potentially interesting hidden endpoints from robots.txt."""
        interesting_patterns = [
            r'/admin',
            r'/api',
            r'/backup',
            r'/config',
            r'/debug',
            r'/private',
            r'/secret',
            r'/test',
            r'/dev',
            r'/staging',
            r'/internal',
            r'/\.git',
            r'/\.svn',
            r'/\.env',
        ]

        hidden: list[str] = []

        for entry in robots_entries:
            for pattern in interesting_patterns:
                if re.search(pattern, entry, re.IGNORECASE):
                    hidden.append(entry)
                    break

        return hidden

    @staticmethod
    def _date_window(target_date: str, days: int = 30) -> tuple[str, str | None]:
        """Return ``(from, to)`` YYYYMMDD bounds spanning ``days`` forward.

        The old implementation added ``days`` to the YYYYMMDD value as an
        integer (e.g. ``20240120 + 30 = 20240150``), which yields invalid
        dates and mishandles month/year boundaries.  Uses real date
        arithmetic instead; if ``target_date`` is malformed the upper bound
        is dropped rather than raising.
        """
        start = target_date[:8]
        try:
            end = datetime.strptime(start, "%Y%m%d") + timedelta(days=days)
        except ValueError:
            return start, None
        return start, end.strftime("%Y%m%d")

    async def get_content_at_date(
        self,
        url: str,
        session: "aiohttp.ClientSession",
        target_date: str,
    ) -> str | None:
        """Get content of URL at a specific date.

        Args:
            url: URL to retrieve
            session: aiohttp session
            target_date: Date in YYYYMMDD format

        Returns:
            Content string or None if not available
        """
        from_date, to_date = self._date_window(target_date, days=30)
        snapshots = await self.get_snapshots(
            url, session,
            from_date=from_date,
            to_date=to_date,
            limit=1,
        )

        if not snapshots:
            return None

        return await self._fetch_snapshot_content(snapshots[0], session)

    # --- Private helpers ---

    @staticmethod
    def _compile_flag_patterns(
        patterns: list[str] | None,
    ) -> list[re.Pattern[str]]:
        """Compile flag regex patterns, with defaults for common CTF formats."""
        return compile_flag_patterns(patterns)

    async def _fetch_snapshot_content(
        self,
        snapshot: WaybackSnapshot,
        session: "aiohttp.ClientSession",
    ) -> str | None:
        """Fetch the text content of a single snapshot."""
        await self._rate_limit_wait()
        try:
            async with session.get(snapshot.wayback_url) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            logger.debug(
                "Failed to get content for %s: %s", snapshot.wayback_url, e
            )
        return None

    async def _scan_snapshot_content(
        self,
        result: WaybackResult,
        session: "aiohttp.ClientSession",
        compiled_flags: list[re.Pattern[str]],
        scan_content: bool = True,
        diff_snapshots: bool = False,
        max_snapshots: int = 5,
    ) -> None:
        """Fetch snapshot content, scan for flags, and optionally diff."""
        # Pick evenly spaced snapshots to maximize coverage
        snapshots = result.snapshots
        if len(snapshots) > max_snapshots:
            step = len(snapshots) / max_snapshots
            indices = [int(i * step) for i in range(max_snapshots)]
            snapshots = [result.snapshots[i] for i in indices]

        prev_content: str | None = None
        prev_ts: str | None = None

        for snapshot in snapshots:
            content = await self._fetch_snapshot_content(snapshot, session)
            if not content:
                continue

            # Strip Wayback toolbar injection
            content = self._strip_wayback_toolbar(content)

            if scan_content:
                # Scan for flags
                for flag in extract_flags(content, compiled_flags):
                    if flag not in result.flags_found:
                        result.flags_found.append(flag)

                # Store excerpt
                plain = re.sub(r'<[^>]+>', ' ', content)
                plain = re.sub(r'\s+', ' ', plain).strip()
                result.historical_content.append({
                    "url": snapshot.original_url,
                    "timestamp": snapshot.timestamp,
                    "excerpt": plain[:500],
                })

            if diff_snapshots and prev_content is not None:
                diff = self._diff_content(
                    prev_ts or "", snapshot.timestamp,
                    prev_content, content,
                )
                if diff.added_lines or diff.removed_lines:
                    result.diffs.append(diff)

                    # Scan diff lines for flags too
                    for line in diff.added_lines + diff.removed_lines:
                        for flag in extract_flags(line, compiled_flags):
                            if flag not in result.flags_found:
                                result.flags_found.append(flag)

            prev_content = content
            prev_ts = snapshot.timestamp

    @staticmethod
    def _strip_wayback_toolbar(html: str) -> str:
        """Remove the Wayback Machine toolbar injection from HTML."""
        # The toolbar is injected between <!-- BEGIN WAYBACK TOOLBAR -->
        # and <!-- END WAYBACK TOOLBAR -->
        html = re.sub(
            r'<!-- BEGIN WAYBACK TOOLBAR -->.*?<!-- END WAYBACK TOOLBAR -->',
            '', html, flags=re.DOTALL,
        )
        # Also remove the wm.* script block
        html = re.sub(
            r'<script[^>]*>.*?__wm\..*?</script>',
            '', html, flags=re.DOTALL,
        )
        return html

    @staticmethod
    def _diff_content(
        old_ts: str, new_ts: str,
        old_content: str, new_content: str,
    ) -> WaybackDiff:
        """Simple line-based diff between two snapshots."""
        # Strip HTML for cleaner diff
        old_text = re.sub(r'<[^>]+>', ' ', old_content)
        new_text = re.sub(r'<[^>]+>', ' ', new_content)

        old_lines = set(
            line.strip() for line in old_text.split('\n') if line.strip()
        )
        new_lines = set(
            line.strip() for line in new_text.split('\n') if line.strip()
        )

        return WaybackDiff(
            old_timestamp=old_ts,
            new_timestamp=new_ts,
            added_lines=sorted(new_lines - old_lines)[:100],
            removed_lines=sorted(old_lines - new_lines)[:100],
        )

    @staticmethod
    def _build_profile_urls(
        username: str,
        platforms: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        """Build profile URLs for a username across platforms."""
        all_urls: dict[str, str] = {
            "github": f"https://github.com/{username}",
            "gitlab": f"https://gitlab.com/{username}",
            "twitter": f"https://twitter.com/{username}",
            "reddit": f"https://reddit.com/user/{username}",
            "instagram": f"https://instagram.com/{username}",
            "linkedin": f"https://linkedin.com/in/{username}",
            "keybase": f"https://keybase.io/{username}",
            "hackernews": f"https://news.ycombinator.com/user?id={username}",
            "medium": f"https://medium.com/@{username}",
            "devto": f"https://dev.to/{username}",
            "stackoverflow": f"https://stackoverflow.com/users/{username}",
            "pastebin": f"https://pastebin.com/u/{username}",
            "mastodon": f"https://mastodon.social/@{username}",
            "youtube": f"https://youtube.com/@{username}",
            "tumblr": f"https://{username}.tumblr.com",
            "wordpress": f"https://{username}.wordpress.com",
            "steam": f"https://steamcommunity.com/id/{username}",
            "twitch": f"https://twitch.tv/{username}",
            "soundcloud": f"https://soundcloud.com/{username}",
            "pinterest": f"https://pinterest.com/{username}",
            "flickr": f"https://flickr.com/people/{username}",
            "behance": f"https://behance.net/{username}",
            "dribbble": f"https://dribbble.com/{username}",
            "codepen": f"https://codepen.io/{username}",
            "tryhackme": f"https://tryhackme.com/p/{username}",
            "hackthebox": f"https://app.hackthebox.com/users/{username}",
            "bluesky": f"https://bsky.app/profile/{username}",
        }

        if platforms:
            return [
                (name, url) for name, url in all_urls.items()
                if name in platforms
            ]
        return list(all_urls.items())
