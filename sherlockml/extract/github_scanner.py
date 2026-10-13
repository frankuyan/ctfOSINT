"""Deep GitHub enumeration for OSINT."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from sherlockml.flags import compile_flag_patterns, find_flags

if TYPE_CHECKING:
    import aiohttp


@dataclass
class GitHubCommit:
    """A GitHub commit with extracted data."""
    sha: str
    message: str
    author_name: str
    author_email: str
    date: str
    url: str
    additions: int = 0
    deletions: int = 0
    files_changed: list[str] = field(default_factory=list)
    

@dataclass
class GitHubGist:
    """A GitHub gist."""
    id: str
    description: str
    url: str
    public: bool
    files: list[str] = field(default_factory=list)
    created_at: str = ""


@dataclass  
class GitHubResult:
    """Complete GitHub scan result."""
    username: str
    profile_url: str
    repos: list[dict[str, Any]] = field(default_factory=list)
    commits: list[GitHubCommit] = field(default_factory=list)
    gists: list[GitHubGist] = field(default_factory=list)
    emails_found: list[str] = field(default_factory=list)
    flags_found: list[str] = field(default_factory=list)
    sensitive_files: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "username": self.username,
            "profile_url": self.profile_url,
            "repos_count": len(self.repos),
            "commits_count": len(self.commits),
            "gists_count": len(self.gists),
            "emails_found": self.emails_found,
            "flags_found": self.flags_found,
            "sensitive_files": self.sensitive_files,
        }


class GitHubScanner:
    """Deep GitHub enumeration for OSINT.
    
    Searches commits, issues, gists for sensitive data.
    Looks for email leaks, CTF flags, API keys, and more.
    
    Example:
        >>> scanner = GitHubScanner(auth_token=os.environ.get("GITHUB_TOKEN"))
        >>> result = await scanner.scan_user("targetuser", commits=True, depth=10)
        >>> print(result.flags_found)
    """
    
    API_BASE = "https://api.github.com"
    
    # Patterns for sensitive data
    FLAG_REGEX = re.compile(
        r'(flag|ctf|glug|hxp|picoCTF|HTB)\{[^}]+\}',
        re.IGNORECASE
    )
    
    EMAIL_REGEX = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    )
    
    # Sensitive file patterns
    SENSITIVE_FILES = [
        r'\.env$',
        r'\.env\.local$',
        r'config\.ya?ml$',
        r'secrets?\.json$',
        r'credentials?\.json$',
        r'\.git/config$',
        r'id_rsa$',
        r'\.pem$',
        r'\.key$',
        r'password',
        r'api[_-]?key',
    ]
    
    def __init__(
        self,
        auth_token: str | None = None,
        rate_limit: float = 30.0,
        flag_patterns: list[str] | None = None,
    ):
        """Initialize the scanner.
        
        Args:
            auth_token: GitHub API token (increases rate limits)
            rate_limit: Requests per minute
            flag_patterns: Flag regexes (e.g. config.ctf.flag_patterns);
                defaults to FLAG_REGEX
        """
        self.auth_token = auth_token
        self.rate_limit = rate_limit
        self.flag_patterns = (
            compile_flag_patterns(flag_patterns) if flag_patterns else [self.FLAG_REGEX]
        )
        self._last_request = 0.0
    
    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SherlockML/1.0",
        }
        if self.auth_token:
            headers["Authorization"] = f"token {self.auth_token}"
        return headers
    
    async def _rate_limit_wait(self) -> None:
        """Wait for rate limiting."""
        import time
        min_interval = 60.0 / self.rate_limit
        elapsed = time.monotonic() - self._last_request
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = time.monotonic()
    
    async def scan_user(
        self,
        username: str,
        session: "aiohttp.ClientSession",
        *,
        commits: bool = True,
        gists: bool = True,
        depth: int = 10,
    ) -> GitHubResult:
        """Comprehensive user scan.
        
        Args:
            username: GitHub username
            session: aiohttp session
            commits: Search commit history
            gists: Search gists
            depth: Number of pages to search
            
        Returns:
            GitHubResult with all findings
        """
        result = GitHubResult(
            username=username,
            profile_url=f"https://github.com/{username}",
        )
        
        # Get user repos
        result.repos = await self._get_repos(username, session)
        
        # Search commits
        if commits:
            result.commits = await self._search_commits(username, session, depth)
            
            # Extract emails and flags from commits
            for commit in result.commits:
                if commit.author_email:
                    result.emails_found.append(commit.author_email)
                
                result.flags_found.extend(find_flags(commit.message, self.flag_patterns))
        
        # Get gists
        if gists:
            result.gists = await self._get_gists(username, session)
        
        # Repo and gist descriptions are already fetched; scan them too
        descriptions = [r.get("description") or "" for r in result.repos]
        descriptions += [g.description or "" for g in result.gists]
        for text in descriptions:
            result.flags_found.extend(find_flags(text, self.flag_patterns))
        
        # Deduplicate, preserving discovery order
        result.emails_found = list(dict.fromkeys(result.emails_found))
        result.flags_found = list(dict.fromkeys(result.flags_found))
        
        return result
    
    async def _get_repos(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> list[dict[str, Any]]:
        """Get user's public repositories."""
        await self._rate_limit_wait()
        
        url = f"{self.API_BASE}/users/{username}/repos"
        params = {"per_page": 100, "sort": "updated"}
        
        try:
            async with session.get(url, headers=self._get_headers(), params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logging.debug("Failed to get repos for %s: %s", username, e)
        
        return []
    
    async def _search_commits(
        self,
        username: str,
        session: "aiohttp.ClientSession",
        depth: int,
    ) -> list[GitHubCommit]:
        """Search commit history for the user."""
        commits: list[GitHubCommit] = []
        
        # Search commits authored by user
        url = f"{self.API_BASE}/search/commits"
        params = {
            "q": f"author:{username}",
            "per_page": 30,
            "sort": "author-date",
        }
        
        for page in range(1, depth + 1):
            await self._rate_limit_wait()
            params["page"] = page
            
            try:
                headers = self._get_headers()
                headers["Accept"] = "application/vnd.github.cloak-preview+json"
                
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        break
                    
                    data = await resp.json()
                    items = data.get("items", [])
                    
                    if not items:
                        break
                    
                    for item in items:
                        commit_data = item.get("commit", {})
                        author = commit_data.get("author", {})
                        
                        commits.append(GitHubCommit(
                            sha=item.get("sha", ""),
                            message=commit_data.get("message", ""),
                            author_name=author.get("name", ""),
                            author_email=author.get("email", ""),
                            date=author.get("date", ""),
                            url=item.get("html_url", ""),
                        ))
                        
            except Exception as e:
                logging.debug("Failed to search commits for %s (page %d): %s", username, page, e)
                break
        
        return commits
    
    async def _get_gists(
        self,
        username: str,
        session: "aiohttp.ClientSession",
    ) -> list[GitHubGist]:
        """Get user's public gists."""
        await self._rate_limit_wait()
        
        url = f"{self.API_BASE}/users/{username}/gists"
        gists: list[GitHubGist] = []
        
        try:
            async with session.get(url, headers=self._get_headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    for item in data:
                        gists.append(GitHubGist(
                            id=item.get("id", ""),
                            description=item.get("description", ""),
                            url=item.get("html_url", ""),
                            public=item.get("public", True),
                            files=list(item.get("files", {}).keys()),
                            created_at=item.get("created_at", ""),
                        ))
        except Exception as e:
            logging.debug("Failed to get gists for %s: %s", username, e)
        
        return gists
    
    async def search_code(
        self,
        query: str,
        session: "aiohttp.ClientSession",
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        """Search GitHub code for a query.
        
        Args:
            query: Search query (e.g., "flag{" or "api_key")
            session: aiohttp session
            max_results: Maximum results to return
            
        Returns:
            List of code search results
        """
        await self._rate_limit_wait()
        
        url = f"{self.API_BASE}/search/code"
        params = {"q": query, "per_page": min(max_results, 100)}
        
        results: list[dict[str, Any]] = []
        
        try:
            async with session.get(url, headers=self._get_headers(), params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("items", [])
        except Exception as e:
            logging.debug("Code search failed for query '%s': %s", query, e)
        
        return results[:max_results]
    
    def extract_emails_from_git_config(self, content: str) -> list[str]:
        """Parse .git/config content for email addresses.
        
        Args:
            content: Contents of .git/config file
            
        Returns:
            List of email addresses found
        """
        emails: list[str] = []
        
        # Look for email in git config
        email_pattern = re.compile(r'email\s*=\s*(.+?)$', re.MULTILINE)
        for match in email_pattern.finditer(content):
            email = match.group(1).strip()
            if self.EMAIL_REGEX.match(email):
                emails.append(email)
        
        # Also find any other emails in the content
        for match in self.EMAIL_REGEX.finditer(content):
            email = match.group(0)
            if email not in emails:
                emails.append(email)
        
        return emails
    
    def find_sensitive_files(self, file_list: list[str]) -> list[str]:
        """Find sensitive files from a list of file paths.
        
        Args:
            file_list: List of file paths
            
        Returns:
            List of sensitive file paths
        """
        sensitive: list[str] = []
        
        for filepath in file_list:
            for pattern in self.SENSITIVE_FILES:
                if re.search(pattern, filepath, re.IGNORECASE):
                    sensitive.append(filepath)
                    break
        
        return sensitive
