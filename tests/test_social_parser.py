"""Tests for social media parser."""

import pytest

from sherlockml.extract.social_parser import SocialMediaParser, SocialProfile


class TestSocialMediaParser:
    """Test suite for social media parsing."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return SocialMediaParser()
    
    def test_extract_rel_me_links(self, parser, sample_html):
        """Test rel=me link extraction."""
        links = parser.extract_rel_me_links(sample_html)
        
        assert len(links) >= 1
        assert any("github.com" in link for link in links)
    
    def test_extract_social_links(self, parser, sample_html):
        """Test social link extraction."""
        links = parser.extract_social_links(sample_html)
        
        # Should find twitter and linkedin
        platforms = [link[0] for link in links]
        assert "twitter" in platforms or "linkedin" in platforms
    
    def test_detect_platform(self, parser):
        """Test platform detection from URL."""
        assert parser.detect_platform("https://github.com/testuser") == ("github", "testuser")
        assert parser.detect_platform("https://twitter.com/test_user") == ("twitter", "test_user")
        assert parser.detect_platform("https://linkedin.com/in/john-doe") == ("linkedin", "john-doe")
        assert parser.detect_platform("https://example.com") is None
    
    def test_extract_timestamps(self, parser):
        """Test timestamp extraction."""
        text = "Posted on 2024-01-15 and updated Jan 20, 2024"
        timestamps = parser.extract_timestamps(text)
        
        assert len(timestamps) >= 1
    
    def test_build_social_graph(self, parser):
        """Test social graph building."""
        profiles = [
            SocialProfile(
                platform="github",
                username="testuser",
                url="https://github.com/testuser",
                linked_accounts=["https://twitter.com/testuser"],
            ),
            SocialProfile(
                platform="twitter",
                username="testuser",
                url="https://twitter.com/testuser",
                linked_accounts=[],
            ),
        ]
        
        graph = parser.build_social_graph(profiles)
        
        assert graph.number_of_nodes() >= 2
        assert graph.number_of_edges() >= 1
    
    def test_find_clusters(self, parser):
        """Test cluster finding."""
        profiles = [
            SocialProfile(
                platform="github", username="user1",
                url="https://github.com/user1",
                linked_accounts=["https://twitter.com/user1"],
            ),
            SocialProfile(
                platform="twitter", username="user1",
                url="https://twitter.com/user1",
                linked_accounts=[],
            ),
            SocialProfile(
                platform="github", username="user2",
                url="https://github.com/user2",
                linked_accounts=[],
            ),
        ]
        
        parser.build_social_graph(profiles)
        clusters = parser.find_clusters()
        
        # user1's github and twitter should be connected
        assert len(clusters) >= 1
    
    def test_get_central_nodes(self, parser):
        """Test PageRank-based central node detection."""
        profiles = [
            SocialProfile(
                platform="github", username="hub",
                url="https://github.com/hub",
                linked_accounts=[
                    "https://twitter.com/hub",
                    "https://linkedin.com/in/hub",
                ],
            ),
            SocialProfile(
                platform="twitter", username="hub",
                url="https://twitter.com/hub",
                linked_accounts=[],
            ),
            SocialProfile(
                platform="linkedin", username="hub",
                url="https://linkedin.com/in/hub",
                linked_accounts=[],
            ),
        ]
        
        parser.build_social_graph(profiles)
        central = parser.get_central_nodes(n=3)
        
        assert len(central) >= 1
    
    def test_export_dot(self, parser, tmp_path):
        """Test DOT export."""
        profiles = [
            SocialProfile(
                platform="github", username="test",
                url="https://github.com/test",
                linked_accounts=[],
            ),
        ]

        parser.build_social_graph(profiles)
        output = tmp_path / "graph.dot"
        dot_content = parser.export_dot(output)

        assert output.exists()
        assert "digraph" in dot_content
        assert "github" in dot_content

    def test_export_dot_escapes_quotes(self, parser, tmp_path):
        """A username with a double-quote must not break the DOT string."""
        profiles = [
            SocialProfile(
                platform="twitter", username='we"ird',
                url="https://twitter.com/weird",
                linked_accounts=[],
            ),
        ]

        parser.build_social_graph(profiles)
        dot_content = parser.export_dot(tmp_path / "graph.dot")

        assert 'we\\"ird' in dot_content
        assert 'we"ird' not in dot_content
