"""Social media profile analysis and graph building."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class SocialProfile:
    """A social media profile."""
    platform: str
    username: str
    url: str
    display_name: str | None = None
    bio: str | None = None
    location: str | None = None
    linked_accounts: list[str] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)
    followers: int | None = None
    following: int | None = None
    

@dataclass
class SocialGraphResult:
    """Result of social graph analysis."""
    root_profile: SocialProfile
    connected_profiles: list[SocialProfile] = field(default_factory=list)
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (from, to, relationship)
    clusters: list[list[str]] = field(default_factory=list)
    
    @property
    def node_count(self) -> int:
        return 1 + len(self.connected_profiles)
    
    @property
    def edge_count(self) -> int:
        return len(self.edges)


class SocialMediaParser:
    """Social media profile analysis and graph building.
    
    Extracts rel="me" links, location patterns, timestamps,
    and builds a social relationship graph using NetworkX.
    
    Example:
        >>> parser = SocialMediaParser()
        >>> links = parser.extract_rel_me_links(html_content)
        >>> graph = parser.build_social_graph(profiles)
        >>> parser.export_graphml(Path("social_graph.graphml"))
    """
    
    # Platform detection patterns
    PLATFORM_PATTERNS = {
        "github": re.compile(r'github\.com/([a-zA-Z0-9_-]+)', re.IGNORECASE),
        "twitter": re.compile(r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)', re.IGNORECASE),
        "linkedin": re.compile(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', re.IGNORECASE),
        "instagram": re.compile(r'instagram\.com/([a-zA-Z0-9_.]+)', re.IGNORECASE),
        "mastodon": re.compile(r'([a-zA-Z0-9.-]+)/@([a-zA-Z0-9_]+)', re.IGNORECASE),
        "keybase": re.compile(r'keybase\.io/([a-zA-Z0-9_]+)', re.IGNORECASE),
        "reddit": re.compile(r'reddit\.com/u(?:ser)?/([a-zA-Z0-9_-]+)', re.IGNORECASE),
        "youtube": re.compile(r'youtube\.com/(?:@|c/|channel/|user/)([a-zA-Z0-9_-]+)', re.IGNORECASE),
        "twitch": re.compile(r'twitch\.tv/([a-zA-Z0-9_]+)', re.IGNORECASE),
        "discord": re.compile(r'discord(?:app)?\.com/users/([0-9]+)', re.IGNORECASE),
    }
    
    # Timestamp patterns (various formats)
    TIMESTAMP_PATTERNS = [
        re.compile(r'\b(\d{4}-\d{2}-\d{2})\b'),  # ISO date
        re.compile(r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b'),  # US date
        re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b', re.IGNORECASE),
    ]
    
    def __init__(self):
        """Initialize the parser."""
        self.graph = nx.DiGraph()
    
    def extract_rel_me_links(self, html: str) -> list[str]:
        """Find rel='me' verification links in HTML.
        
        Args:
            html: HTML content to parse
            
        Returns:
            List of verified linked URLs
        """
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        
        # Find all links with rel="me"
        for a_tag in soup.find_all("a", rel=lambda x: x and "me" in x):
            href = a_tag.get("href")
            if href:
                links.append(href)
        
        # Also check for link tags
        for link_tag in soup.find_all("link", rel=lambda x: x and "me" in x):
            href = link_tag.get("href")
            if href:
                links.append(href)
        
        return list(set(links))
    
    def extract_social_links(self, html: str) -> list[tuple[str, str, str]]:
        """Extract all social media links from HTML.
        
        Args:
            html: HTML content to parse
            
        Returns:
            List of (platform, username, url) tuples
        """
        soup = BeautifulSoup(html, "lxml")
        results: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        
        # Find all links
        for a_tag in soup.find_all("a", href=True):
            url = a_tag.get("href", "")
            
            for platform, pattern in self.PLATFORM_PATTERNS.items():
                match = pattern.search(url)
                if match:
                    username = match.group(1) if len(match.groups()) == 1 else match.group(2)
                    
                    key = (platform, username.lower())
                    if key not in seen:
                        seen.add(key)
                        results.append((platform, username, url))
                    break
        
        return results
    
    def extract_timestamps(self, text: str) -> list[str]:
        """Extract timestamp patterns from text.
        
        Args:
            text: Text content to search
            
        Returns:
            List of timestamp strings found
        """
        timestamps: list[str] = []
        
        for pattern in self.TIMESTAMP_PATTERNS:
            for match in pattern.finditer(text):
                timestamps.append(match.group(0))
        
        return timestamps
    
    def detect_platform(self, url: str) -> tuple[str, str] | None:
        """Detect platform and username from URL.
        
        Args:
            url: URL to analyze
            
        Returns:
            (platform, username) tuple or None
        """
        for platform, pattern in self.PLATFORM_PATTERNS.items():
            match = pattern.search(url)
            if match:
                username = match.group(1) if len(match.groups()) == 1 else match.group(2)
                return (platform, username)
        
        return None
    
    def build_social_graph(
        self,
        profiles: list[SocialProfile],
    ) -> nx.DiGraph:
        """Construct social relationship graph.
        
        Args:
            profiles: List of social profiles to connect
            
        Returns:
            NetworkX DiGraph of relationships
        """
        self.graph.clear()
        
        # Add all profiles as nodes
        for profile in profiles:
            node_id = f"{profile.platform}:{profile.username}"
            self.graph.add_node(
                node_id,
                platform=profile.platform,
                username=profile.username,
                url=profile.url,
                display_name=profile.display_name,
                bio=profile.bio,
                location=profile.location,
            )
        
        # Connect profiles based on linked accounts
        for profile in profiles:
            source_id = f"{profile.platform}:{profile.username}"
            
            for linked_url in profile.linked_accounts:
                detected = self.detect_platform(linked_url)
                if detected:
                    platform, username = detected
                    target_id = f"{platform}:{username}"
                    
                    # Add edge if target exists or create new node
                    if target_id not in self.graph:
                        self.graph.add_node(
                            target_id,
                            platform=platform,
                            username=username,
                            url=linked_url,
                        )
                    
                    self.graph.add_edge(source_id, target_id, relationship="linked")
        
        # Find same-username connections
        usernames: dict[str, list[str]] = {}
        for node_id in self.graph.nodes():
            username = self.graph.nodes[node_id].get("username", "").lower()
            if username:
                if username not in usernames:
                    usernames[username] = []
                usernames[username].append(node_id)
        
        # Connect nodes with same username
        for nodes in usernames.values():
            if len(nodes) > 1:
                for i, node1 in enumerate(nodes):
                    for node2 in nodes[i + 1:]:
                        if not self.graph.has_edge(node1, node2):
                            self.graph.add_edge(node1, node2, relationship="same_username")
        
        return self.graph
    
    def find_clusters(self) -> list[list[str]]:
        """Find connected components in the graph.
        
        Returns:
            List of node ID clusters
        """
        if not self.graph:
            return []
        
        # Convert to undirected for component analysis
        undirected = self.graph.to_undirected()
        components = list(nx.connected_components(undirected))
        
        return [list(c) for c in components]
    
    def get_central_nodes(self, n: int = 5) -> list[tuple[str, float]]:
        """Get most central nodes using PageRank.
        
        Args:
            n: Number of top nodes to return
            
        Returns:
            List of (node_id, score) tuples
        """
        if not self.graph or not self.graph.nodes():
            return []

        try:
            pagerank = nx.pagerank(self.graph)
        except nx.PowerIterationFailedConvergence:
            logger.warning("PageRank failed to converge; returning no central nodes")
            return []
        except ImportError:
            # networkx.pagerank needs scipy; surface the misconfiguration
            # instead of silently pretending there are no central nodes.
            logger.warning(
                "PageRank unavailable (scipy not installed); "
                "install the 'scipy' dependency to enable centrality analysis"
            )
            return []

        sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:n]
    
    def export_graphml(self, path: str | Any) -> None:
        """Export graph to GraphML format.
        
        Args:
            path: Output file path
        """
        nx.write_graphml(self.graph, path)
    
    @staticmethod
    def _dot_escape(value: str) -> str:
        """Escape backslashes then double-quotes for a DOT string literal.

        Backslashes first so quotes escaped afterwards are not re-processed.
        """
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    def export_dot(self, path: str | Any) -> str:
        """Export graph to Graphviz DOT format.

        Args:
            path: Output file path

        Returns:
            DOT format string
        """
        dot_lines = ["digraph SocialGraph {"]
        dot_lines.append('  rankdir=LR;')
        dot_lines.append('  node [shape=box, style=filled];')

        # Color by platform
        platform_colors = {
            "github": "#24292e",
            "twitter": "#1da1f2",
            "linkedin": "#0077b5",
            "instagram": "#e1306c",
            "mastodon": "#6364ff",
            "reddit": "#ff4500",
            "youtube": "#ff0000",
        }

        # Add nodes
        for node_id in self.graph.nodes():
            node_data = self.graph.nodes[node_id]
            platform = node_data.get("platform", "other")
            color = platform_colors.get(platform, "#cccccc")
            username = node_data.get("username", node_id)

            label = f"{self._dot_escape(username)}\\n({self._dot_escape(platform)})"
            dot_lines.append(
                f'  "{self._dot_escape(node_id)}" [label="{label}", '
                f'fillcolor="{color}", fontcolor="white"];'
            )

        # Add edges
        for source, target, data in self.graph.edges(data=True):
            relationship = data.get("relationship", "")
            style = "solid" if relationship == "linked" else "dashed"
            dot_lines.append(
                f'  "{self._dot_escape(source)}" -> "{self._dot_escape(target)}" [style={style}];'
            )
        
        dot_lines.append("}")
        
        dot_content = "\n".join(dot_lines)
        
        # Write to file
        from pathlib import Path
        Path(path).write_text(dot_content)
        
        return dot_content
    
    def analyze_profile(
        self,
        html: str,
        url: str,
    ) -> SocialProfile | None:
        """Analyze a profile page and extract information.
        
        Args:
            html: HTML content of profile page
            url: URL of the profile
            
        Returns:
            SocialProfile or None if detection fails
        """
        detected = self.detect_platform(url)
        if not detected:
            return None
        
        platform, username = detected
        
        soup = BeautifulSoup(html, "lxml")
        
        # Extract common fields
        bio = None
        display_name = None
        location = None
        
        # Try common meta tags
        og_title = soup.find("meta", property="og:title")
        if og_title:
            display_name = og_title.get("content")
        
        og_description = soup.find("meta", property="og:description")
        if og_description:
            bio = og_description.get("content")
        
        # Extract linked accounts
        linked = self.extract_rel_me_links(html)
        social_links = self.extract_social_links(html)
        
        return SocialProfile(
            platform=platform,
            username=username,
            url=url,
            display_name=display_name,
            bio=bio,
            location=location,
            linked_accounts=linked + [s[2] for s in social_links],
            timestamps=self.extract_timestamps(html),
        )
