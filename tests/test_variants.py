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


class TestGenerateBasic:
    """Tests for the lightweight default variant generator."""

    def test_multi_part_separator_swaps(self):
        gen = UsernameVariants()
        out = set(gen.generate_basic("john_doe", max_variants=99))
        assert "johndoe" in out
        assert "john.doe" in out
        assert "john-doe" in out

    def test_multi_part_reversed(self):
        gen = UsernameVariants()
        out = set(gen.generate_basic("john_doe", max_variants=99))
        assert any(v in out for v in ("doe_john", "doejohn", "doe.john", "doe-john"))

    def test_multi_part_first_initial(self):
        gen = UsernameVariants()
        out = set(gen.generate_basic("john_doe", max_variants=99))
        assert any(v in out for v in ("jdoe", "j_doe", "j.doe", "j-doe"))

    def test_multi_part_reverse_initial(self):
        gen = UsernameVariants()
        out = set(gen.generate_basic("john_doe", max_variants=99))
        assert any(v in out for v in ("johnd", "john_d", "john.d", "john-d"))

    def test_digit_suffixes(self):
        gen = UsernameVariants()
        out = set(gen.generate_basic("alice", max_variants=99))
        assert {"alice1", "alice01", "alice2024", "alice2025"}.issubset(out)

    def test_excludes_original(self):
        gen = UsernameVariants()
        assert "john_doe" not in gen.generate_basic("john_doe", max_variants=99)
        assert "alice" not in gen.generate_basic("alice", max_variants=99)

    def test_max_variants_cap(self):
        gen = UsernameVariants()
        out = gen.generate_basic("john_doe", max_variants=5)
        assert len(out) <= 5

    def test_leading_trailing_separators_degrade_gracefully(self):
        gen = UsernameVariants()
        # '_alice_' -> parts ['', 'alice', ''] -> filtered to ['alice'] -> single-part path
        out = gen.generate_basic("_alice_", max_variants=99)
        assert all(v for v in out), "empty string leaked into variants"
        assert "alice1" in out

    def test_three_part_name(self):
        gen = UsernameVariants()
        out = set(gen.generate_basic("john.q.doe", max_variants=99))
        assert "johnqdoe" in out  # concatenated
        # Reversed full: doe.q.john / doe_q_john / etc.
        assert any(v in out for v in ("doe.q.john", "doe_q_john", "doe-q-john", "doeqjohn"))

    def test_only_valid_usernames_returned(self):
        gen = UsernameVariants()
        # All variants should pass _is_valid_username (no consecutive separators, len <= 30)
        for base in ("john_doe", "alice", "JohnDoe", "_alice_", "a_b_c_d"):
            for v in gen.generate_basic(base, max_variants=99):
                assert "__" not in v and ".." not in v and "--" not in v
                assert 1 <= len(v) <= 30


class TestExistingGenerateNotRegressed:
    """Smoke-checks that the wider generate() path still does what it did."""

    def test_generate_returns_input(self):
        gen = UsernameVariants()
        assert "testuser" in gen.generate("testuser")

    def test_generate_with_leet(self):
        gen = UsernameVariants()
        out = gen.generate("test", leet=True)
        assert any(c.isdigit() for v in out for c in v)
