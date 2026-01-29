"""Tests for username variant generation."""

import pytest

from sherlockml.enum.variants import UsernameVariants, parse_years


class TestUsernameVariants:
    """Test suite for UsernameVariants class."""
    
    def test_basic_generation(self):
        """Test basic variant generation."""
        gen = UsernameVariants()
        variants = gen.generate("testuser")
        
        assert "testuser" in variants
        assert "TESTUSER" in variants
        assert "testuser" in variants
    
    def test_leet_generation(self):
        """Test leetspeak variant generation."""
        gen = UsernameVariants()
        variants = gen.generate("test", leet=True)
        
        assert "t3st" in variants or "7357" in variants
    
    def test_year_suffixes(self):
        """Test year suffix generation."""
        gen = UsernameVariants()
        variants = gen.generate("user", years=(2020, 2022))
        
        assert "user2020" in variants
        assert "user2021" in variants
        assert "user2022" in variants
        assert "user21" in variants  # Short year format
    
    def test_separator_variants(self):
        """Test separator variants."""
        gen = UsernameVariants()
        variants = gen.generate("john", prefixes=["the"])
        
        assert "thejohn" in variants or "the_john" in variants
    
    def test_common_prefixes(self):
        """Test common prefix/suffix generation."""
        gen = UsernameVariants()
        variants = gen.generate("user", include_common=True)
        
        # Should include some common prefixes
        assert any("real" in v.lower() for v in variants)
    
    def test_max_variants_limit(self):
        """Test maximum variants limit."""
        gen = UsernameVariants()
        variants = gen.generate(
            "test",
            leet=True,
            include_common=True,
            years=(2015, 2025),
            max_variants=50,
        )
        
        assert len(variants) <= 50
    
    def test_invalid_username_filtering(self):
        """Test that invalid usernames are filtered."""
        gen = UsernameVariants()
        variants = gen.generate("test")
        
        # No consecutive special characters
        assert not any("__" in v for v in variants)
        assert not any(".." in v for v in variants)
    
    def test_fuzzy_match(self):
        """Test Jaro-Winkler fuzzy matching."""
        gen = UsernameVariants(fuzzy_threshold=0.8)
        
        assert gen.fuzzy_match("testuser", "testuser1")
        assert gen.fuzzy_match("johndoe", "john_doe")
        assert not gen.fuzzy_match("alice", "bob")
    
    def test_similarity_ranking(self):
        """Test similarity-based ranking."""
        gen = UsernameVariants()
        variants = ["testuser", "test_user", "testuser123", "randomname"]
        
        ranked = gen.rank_by_similarity(variants, "testuser")
        
        # testuser should be first (exact match)
        assert ranked[0][0] == "testuser"
        assert ranked[0][1] == 1.0
    
    def test_filter_by_similarity(self):
        """Test filtering variants by similarity."""
        gen = UsernameVariants()
        variants = ["testuser", "test_user", "randomname", "xyz"]
        
        filtered = gen.filter_by_similarity(variants, "testuser", threshold=0.7)
        
        assert "testuser" in filtered
        assert "test_user" in filtered
        assert "xyz" not in filtered


class TestParseYears:
    """Test year range parsing."""
    
    def test_valid_range(self):
        """Test valid year range parsing."""
        start, end = parse_years("2020-2025")
        
        assert start == 2020
        assert end == 2025
    
    def test_invalid_format(self):
        """Test invalid format raises error."""
        with pytest.raises(ValueError):
            parse_years("2020")
        
        with pytest.raises(ValueError):
            parse_years("20-25")
    
    def test_inverted_range(self):
        """Test inverted range raises error."""
        with pytest.raises(ValueError):
            parse_years("2025-2020")
