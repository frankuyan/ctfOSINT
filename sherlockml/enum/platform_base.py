"""Base platform interface for SherlockML."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp

# Default realistic browser User-Agent
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class PlatformCategory(Enum):
    """Categories of platforms for organization and filtering."""
    SOCIAL = "social"
    CODE = "code"
    PROFESSIONAL = "professional"
    GAMING = "gaming"
    CREATIVE = "creative"
    FORUM = "forum"
    DATING = "dating"
    MUSIC = "music"
    VIDEO = "video"
    NEWS = "news"
    CRYPTO = "crypto"
    OTHER = "other"


@dataclass
class PlatformResult:
    """Result from checking a username on a platform."""
    exists: bool
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    response_time: float = 0.0
    error: str | None = None
    raw_response: str | None = None
    
    @property
    def success(self) -> bool:
        """Check if the request was successful (no errors)."""
        return self.error is None


@dataclass
class PlatformMetadata:
    """Extracted metadata from a platform profile."""
    bio: str | None = None
    display_name: str | None = None
    location: str | None = None
    website: str | None = None
    email: str | None = None
    created_at: str | None = None
    followers: int | None = None
    following: int | None = None
    posts_count: int | None = None
    verified: bool = False
    profile_image: str | None = None
    linked_accounts: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)


class BasePlatform(ABC):
    """Abstract base class for platform modules.
    
    All platform implementations must inherit from this class and implement
    the required abstract methods.
    
    Attributes:
        name: Unique identifier for the platform
        display_name: Human-readable platform name
        base_url: Base URL for the platform
        url_template: Template for username URLs (use {username} placeholder)
        category: Platform category for filtering
        requires_auth: Whether API auth is required
        rate_limit_rpm: Requests per minute limit
    """
    
    name: str
    display_name: str
    base_url: str
    url_template: str
    category: PlatformCategory = PlatformCategory.OTHER
    requires_auth: bool = False
    rate_limit_rpm: float = 60.0  # requests per minute
    
    def __init__(self, auth_token: str | None = None):
        """Initialize the platform.
        
        Args:
            auth_token: Optional authentication token
        """
        self.auth_token = auth_token
        self._session: aiohttp.ClientSession | None = None
    
    @property
    def rate_limit_rps(self) -> float:
        """Rate limit in requests per second."""
        return self.rate_limit_rpm / 60.0
    
    def get_url(self, username: str) -> str:
        """Get the profile URL for a username.
        
        Args:
            username: Username to check
            
        Returns:
            Full profile URL
        """
        return self.url_template.format(username=username)
    
    @abstractmethod
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check if username exists on this platform.
        
        Args:
            username: Username to check
            session: aiohttp session for making requests
            
        Returns:
            PlatformResult with existence status and metadata
        """
        ...
    
    async def extract_metadata(
        self,
        url: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformMetadata:
        """Extract detailed metadata from a profile.
        
        Default implementation returns empty metadata.
        Override in subclasses for platform-specific extraction.
        
        Args:
            url: Profile URL to extract from
            session: aiohttp session for making requests
            
        Returns:
            PlatformMetadata with extracted information
        """
        return PlatformMetadata()
    
    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for requests to this platform.
        
        Override in subclasses to add platform-specific headers.
        
        Returns:
            Dictionary of headers
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        return headers
    
    def validate_username(self, username: str) -> bool:
        """Check if username format is valid for this platform.
        
        Default implementation accepts most usernames.
        Override for platform-specific validation.
        
        Args:
            username: Username to validate
            
        Returns:
            True if username format is valid
        """
        if not username or len(username) > 50:
            return False
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r})>"


class HTTPCheckPlatform(BasePlatform):
    """Base class for platforms that use simple HTTP status checks.

    Makes GET requests and checks status codes plus response body
    content to determine if a profile exists.
    """

    check_method: str = "GET"
    exists_status_codes: set[int] = {200}
    not_found_status_codes: set[int] = {404}

    # Common text patterns indicating a profile was NOT found (soft 404 detection).
    # Subclasses can override with platform-specific patterns.
    not_found_text_patterns: list[str] = [
        r"(?i)page\s+not\s+found",
        r"(?i)user\s+not\s+found",
        r"(?i)profile\s+not\s+found",
        r"(?i)account\s+(has\s+been\s+)?(suspended|deleted|removed|deactivated|banned)",
        r"(?i)this\s+page\s+doesn.?t\s+exist",
        r"(?i)404\s*[-–—:]\s*not\s+found",
        r"(?i)sorry,\s+nobody\s+.*that\s+name",
        r"(?i)the\s+page\s+you\s+(were|are)\s+looking\s+for",
    ]

    # Max bytes to read from response body (avoid downloading huge pages)
    _max_body_bytes: int = 512 * 1024  # 512 KB

    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check username existence via HTTP status code and body content."""
        import time

        if not self.validate_username(username):
            return PlatformResult(
                exists=False,
                error=f"Invalid username format for {self.name}",
            )

        url = self.get_url(username)
        headers = self.get_headers()

        start_time = time.monotonic()

        try:
            method = session.head if self.check_method == "HEAD" else session.get
            async with method(url, headers=headers, allow_redirects=True) as response:
                response_time = time.monotonic() - start_time
                status = response.status

                # Read body for GET requests
                body = ""
                if self.check_method != "HEAD":
                    raw = await response.content.read(self._max_body_bytes)
                    body = raw.decode("utf-8", errors="replace")

                metadata: dict[str, Any] = {}

                # Extract page title from body
                if body:
                    title_match = re.search(
                        r"<title[^>]*>(.*?)</title>", body, re.IGNORECASE | re.DOTALL
                    )
                    if title_match:
                        metadata["title"] = title_match.group(1).strip()

                if status in self.exists_status_codes:
                    # Check for soft 404: site returns 200 but page says "not found"
                    if body and self._is_soft_404(body):
                        return PlatformResult(
                            exists=False,
                            url=None,
                            confidence=0.8,
                            response_time=response_time,
                            raw_response=body,
                            metadata=metadata,
                        )

                    return PlatformResult(
                        exists=True,
                        url=url,
                        confidence=0.9,
                        response_time=response_time,
                        raw_response=body or None,
                        metadata=metadata,
                    )
                elif status in self.not_found_status_codes:
                    return PlatformResult(
                        exists=False,
                        url=None,
                        confidence=0.95,
                        response_time=response_time,
                        raw_response=body or None,
                        metadata=metadata,
                    )
                else:
                    return PlatformResult(
                        exists=False,
                        confidence=0.3,
                        response_time=response_time,
                        error=f"Unexpected status code: {status}",
                        raw_response=body or None,
                        metadata=metadata,
                    )

        except Exception as e:
            return PlatformResult(
                exists=False,
                error=str(e),
                response_time=time.monotonic() - start_time,
            )

    def _is_soft_404(self, body: str) -> bool:
        """Check if a 200-status response body is actually a 'not found' page."""
        for pattern in self.not_found_text_patterns:
            if re.search(pattern, body):
                return True
        return False
