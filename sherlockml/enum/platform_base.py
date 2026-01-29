"""Base platform interface for SherlockML."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import aiohttp


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
    
    Many platforms can be checked by making a HEAD or GET request
    and checking for 200 vs 404 status codes.
    """
    
    check_method: str = "HEAD"  # HEAD or GET
    exists_status_codes: set[int] = {200}
    not_found_status_codes: set[int] = {404}
    
    async def check_username(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> PlatformResult:
        """Check username existence via HTTP status code."""
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
                
                if status in self.exists_status_codes:
                    return PlatformResult(
                        exists=True,
                        url=url,
                        confidence=0.9,
                        response_time=response_time,
                    )
                elif status in self.not_found_status_codes:
                    return PlatformResult(
                        exists=False,
                        url=None,
                        confidence=0.95,
                        response_time=response_time,
                    )
                else:
                    # Ambiguous status code
                    return PlatformResult(
                        exists=False,
                        confidence=0.3,
                        response_time=response_time,
                        error=f"Unexpected status code: {status}",
                    )
                    
        except Exception as e:
            return PlatformResult(
                exists=False,
                error=str(e),
                response_time=time.monotonic() - start_time,
            )
