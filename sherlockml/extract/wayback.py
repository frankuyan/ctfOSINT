"""Wayback Machine integration for historical profile analysis."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    import aiohttp


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
class WaybackResult:
    """Result from Wayback Machine analysis."""
    original_url: str
    snapshots: list[WaybackSnapshot] = field(default_factory=list)
    hidden_endpoints: list[str] = field(default_factory=list)
    robots_entries: list[str] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)
    historical_content: list[dict[str, Any]] = field(default_factory=list)
    
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


class WaybackIntegration:
    """Internet Archive CDX API integration.
    
    Query historical snapshots, extract hidden endpoints from
    robots.txt and sitemap.xml, analyze profile changes over time.
    
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
            logging.debug("Failed to get snapshots for %s: %s", url, e)
        
        return snapshots
    
    async def analyze_url(
        self,
        url: str,
        session: "aiohttp.ClientSession",
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> WaybackResult:
        """Full analysis of a URL's historical data.
        
        Args:
            url: URL to analyze
            session: aiohttp session
            from_date: Start date filter
            to_date: End date filter
            
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
        
        # Check robots.txt
        result.robots_entries = await self.extract_robots_entries(
            base_url, session
        )
        
        # Check sitemap.xml
        result.sitemap_urls = await self.extract_sitemap_urls(
            base_url, session
        )
        
        # Find hidden endpoints
        result.hidden_endpoints = self._find_hidden_endpoints(
            result.robots_entries
        )
        
        return result
    
    async def extract_robots_entries(
        self,
        base_url: str,
        session: "aiohttp.ClientSession",
    ) -> list[str]:
        """Extract entries from historical robots.txt.
        
        Args:
            base_url: Base URL of the site
            session: aiohttp session
            
        Returns:
            List of disallowed/allowed paths
        """
        robots_url = f"{base_url}/robots.txt"
        entries: list[str] = []
        
        # Get historical robots.txt
        snapshots = await self.get_snapshots(robots_url, session, limit=5)
        
        for snapshot in snapshots[:3]:  # Check a few snapshots
            await self._rate_limit_wait()
            
            try:
                async with session.get(snapshot.wayback_url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        
                        # Parse robots.txt entries
                        for line in text.split("\n"):
                            line = line.strip()
                            if line.startswith(("Disallow:", "Allow:")):
                                path = line.split(":", 1)[1].strip()
                                if path and path not in entries:
                                    entries.append(path)
                                    
            except Exception as e:
                logging.debug("Failed to fetch robots.txt snapshot: %s", e)
                continue
        
        return entries
    
    async def extract_sitemap_urls(
        self,
        base_url: str,
        session: "aiohttp.ClientSession",
    ) -> list[str]:
        """Extract URLs from historical sitemap.xml.
        
        Args:
            base_url: Base URL of the site
            session: aiohttp session
            
        Returns:
            List of URLs from sitemap
        """
        sitemap_url = f"{base_url}/sitemap.xml"
        urls: list[str] = []
        
        # Get historical sitemap
        snapshots = await self.get_snapshots(sitemap_url, session, limit=3)
        
        for snapshot in snapshots[:2]:
            await self._rate_limit_wait()
            
            try:
                async with session.get(snapshot.wayback_url) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        
                        # Extract URLs from sitemap XML
                        url_pattern = re.compile(r'<loc>([^<]+)</loc>')
                        for match in url_pattern.finditer(text):
                            url = match.group(1)
                            if url not in urls:
                                urls.append(url)
                                
            except Exception as e:
                logging.debug("Failed to fetch sitemap snapshot: %s", e)
                continue
        
        return urls
    
    def _find_hidden_endpoints(self, robots_entries: list[str]) -> list[str]:
        """Find potentially interesting hidden endpoints.
        
        Args:
            robots_entries: Entries from robots.txt
            
        Returns:
            List of interesting endpoints
        """
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
        # Find closest snapshot
        snapshots = await self.get_snapshots(
            url, session,
            from_date=target_date[:8],
            to_date=str(int(target_date[:8]) + 30),
            limit=1,
        )
        
        if not snapshots:
            return None
        
        await self._rate_limit_wait()
        
        try:
            async with session.get(snapshots[0].wayback_url) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            logging.debug("Failed to get content at date %s for %s: %s", target_date, url, e)
        
        return None
