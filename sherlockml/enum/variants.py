"""Username variant generation for OSINT enumeration."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

import jellyfish


@dataclass
class VariantConfig:
    """Configuration for variant generation."""
    leet: bool = False
    separators: list[str] = field(default_factory=lambda: ['', '_', '.', '-'])
    prefixes: list[str] = field(default_factory=list)
    suffixes: list[str] = field(default_factory=list)
    years: tuple[int, int] | None = None
    max_variants: int = 1000


class UsernameVariants:
    """Generate username permutations for OSINT enumeration.
    
    Supports:
    - Leetspeak transformations (a→4, e→3, etc.)
    - Separator variations (_, ., -)
    - Prefix/suffix additions
    - Year suffixes (common in usernames)
    - Jaro-Winkler fuzzy matching for similarity checks
    """
    
    # Standard leetspeak mappings
    LEET_MAP: dict[str, str] = {
        'a': '4', 'A': '4',
        'e': '3', 'E': '3',
        'i': '1', 'I': '1',
        'o': '0', 'O': '0',
        's': '5', 'S': '5',
        't': '7', 'T': '7',
        'l': '1', 'L': '1',
        'b': '8', 'B': '8',
        'g': '9', 'G': '9',
    }
    
    # Common separators used in usernames
    DEFAULT_SEPARATORS: list[str] = ['', '_', '.', '-']
    
    # Common prefixes used in usernames
    COMMON_PREFIXES: list[str] = [
        'the', 'real', 'official', 'its', 'im', 'i_am', 'notthe',
        'x', 'xx', 'mr', 'ms', 'dr', 'prof',
    ]
    
    # Common suffixes used in usernames
    COMMON_SUFFIXES: list[str] = [
        'official', 'real', 'hd', 'tv', 'gaming', 'dev', 'code',
        'sec', 'security', 'hack', 'ctf', 'pwn',
    ]
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """Initialize variant generator.
        
        Args:
            fuzzy_threshold: Jaro-Winkler similarity threshold (0.0-1.0)
        """
        self.fuzzy_threshold = fuzzy_threshold
    
    def generate_basic(self, base: str) -> list[str]:
        """Generate lightweight variants by splitting and recombining with separators.

        Always produces a small, high-quality set of alternatives based on the
        structure of the input username.  This is fast and is called by default
        even when the ``--variants`` flag is not used.

        Transformations applied:
        - Split on common separators (``_``, ``.``, ``-``) and rejoin with each
        - Case variants (lower, original)
        - Remove all separators (concatenated form)
        - First-initial + last-name style (``jdoe`` from ``john_doe``)

        Returns:
            Deduplicated list of valid username variants (excluding the
            original, which the caller already has).
        """
        variants: set[str] = set()

        # Split username on separators
        parts = re.split(r'[_.\-]', base)

        if len(parts) > 1:
            # Recombine with each separator style
            for sep in self.DEFAULT_SEPARATORS:
                variants.add(sep.join(parts))
                variants.add(sep.join(p.lower() for p in parts))

            # First-initial variants: jdoe, j_doe, j.doe
            if len(parts[0]) >= 1:
                initial = parts[0][0].lower()
                rest = parts[-1].lower()
                for sep in self.DEFAULT_SEPARATORS:
                    variants.add(f"{initial}{sep}{rest}")
        else:
            # No separator in original — try adding common splits
            variants.add(base.lower())

        # Case variant
        variants.add(base.lower())

        # Remove the original so caller doesn't double-add it
        variants.discard(base)

        return [v for v in sorted(variants) if v and self._is_valid_username(v)]

    def generate(
        self,
        base: str,
        *,
        leet: bool = False,
        separators: list[str] | None = None,
        prefixes: list[str] | None = None,
        suffixes: list[str] | None = None,
        years: tuple[int, int] | None = None,
        include_common: bool = False,
        max_variants: int = 1000,
    ) -> list[str]:
        """Generate all username variant combinations.
        
        Args:
            base: Base username to generate variants from
            leet: Enable leetspeak transformations
            separators: List of separators to use between parts
            prefixes: List of prefixes to prepend
            suffixes: List of suffixes to append
            years: Tuple of (start_year, end_year) for year suffixes
            include_common: Include common prefixes/suffixes
            max_variants: Maximum number of variants to generate
            
        Returns:
            List of unique username variants
        """
        if separators is None:
            separators = self.DEFAULT_SEPARATORS
        
        if prefixes is None:
            prefixes = []
        if include_common:
            prefixes = list(set(prefixes + self.COMMON_PREFIXES))
        
        if suffixes is None:
            suffixes = []
        if include_common:
            suffixes = list(set(suffixes + self.COMMON_SUFFIXES))
        
        variants: set[str] = {base}
        
        # Generate base transformations
        base_forms = [base, base.lower(), base.upper()]
        if leet:
            base_forms.extend(self._leet_variants(base))
        base_forms = list(set(base_forms))
        
        # Add year suffixes
        year_suffixes: list[str] = ['']
        if years:
            start, end = years
            year_suffixes.extend(str(y) for y in range(start, end + 1))
            year_suffixes.extend(str(y)[-2:] for y in range(start, end + 1))
        
        # Generate all combinations
        for base_form in base_forms:
            # Just the base form with years
            for year in year_suffixes:
                variants.add(f"{base_form}{year}")
            
            # With prefixes
            for prefix, sep in itertools.product([''] + prefixes, separators):
                if prefix:
                    for year in year_suffixes:
                        variants.add(f"{prefix}{sep}{base_form}{year}")
            
            # With suffixes
            for suffix, sep in itertools.product([''] + suffixes, separators):
                if suffix:
                    for year in year_suffixes:
                        variants.add(f"{base_form}{sep}{suffix}{year}")
            
            # With both prefix and suffix (limited combinations)
            if prefixes and suffixes:
                for prefix, suffix in itertools.product(prefixes[:3], suffixes[:3]):
                    for sep in separators:
                        variants.add(f"{prefix}{sep}{base_form}{sep}{suffix}")
        
        # Clean up variants
        result = [v for v in variants if v and self._is_valid_username(v)]
        
        # Limit results
        return sorted(set(result))[:max_variants]
    
    def _leet_variants(self, text: str) -> list[str]:
        """Generate leetspeak variants of text.
        
        Generates variants with different levels of leetspeak transformation.
        """
        variants: list[str] = []
        
        # Full leet transformation
        full_leet = ''.join(self.LEET_MAP.get(c, c) for c in text)
        variants.append(full_leet)
        
        # Partial transformations (one character at a time)
        for i, char in enumerate(text):
            if char.lower() in self.LEET_MAP:
                new_text = text[:i] + self.LEET_MAP.get(char, char) + text[i+1:]
                variants.append(new_text)
        
        return variants
    
    def _is_valid_username(self, username: str) -> bool:
        """Check if a username is valid for most platforms.
        
        Most platforms require:
        - Length between 1 and 30 characters
        - Alphanumeric with limited special characters
        - No consecutive special characters
        """
        if not username or len(username) > 30:
            return False
        
        # Allow alphanumeric, underscore, dot, dash
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            return False

        # No consecutive special characters
        if re.search(r'[_.-]{2,}', username):
            return False
        
        return True
    
    def fuzzy_match(self, candidate: str, target: str, threshold: float | None = None) -> bool:
        """Check if candidate is similar to target using Jaro-Winkler.
        
        Args:
            candidate: Username to check
            target: Target username to compare against
            threshold: Similarity threshold (0.0-1.0), defaults to instance threshold
            
        Returns:
            True if similarity >= threshold
        """
        if threshold is None:
            threshold = self.fuzzy_threshold
        
        similarity = self.jaro_winkler_similarity(candidate, target)
        return similarity >= threshold
    
    def jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        return jellyfish.jaro_winkler_similarity(s1.lower(), s2.lower())
    
    def filter_by_similarity(
        self,
        variants: list[str],
        target: str,
        threshold: float | None = None,
    ) -> list[str]:
        """Filter variants to only those similar to target.
        
        Args:
            variants: List of username variants
            target: Target username to compare against
            threshold: Minimum similarity threshold
            
        Returns:
            Filtered list of similar variants
        """
        if threshold is None:
            threshold = self.fuzzy_threshold
        
        return [v for v in variants if self.fuzzy_match(v, target, threshold)]
    
    def rank_by_similarity(
        self,
        variants: list[str],
        target: str,
    ) -> list[tuple[str, float]]:
        """Rank variants by similarity to target.
        
        Args:
            variants: List of username variants
            target: Target username to compare against
            
        Returns:
            List of (variant, similarity) tuples, sorted by similarity descending
        """
        scored = [(v, self.jaro_winkler_similarity(v, target)) for v in variants]
        return sorted(scored, key=lambda x: x[1], reverse=True)


def parse_years(years_str: str) -> tuple[int, int]:
    """Parse a year range string like '2015-2025'.
    
    Args:
        years_str: String in format 'YYYY-YYYY'
        
    Returns:
        Tuple of (start_year, end_year)
        
    Raises:
        ValueError: If string format is invalid
    """
    match = re.match(r'(\d{4})-(\d{4})', years_str)
    if not match:
        raise ValueError(f"Invalid year range format: {years_str}. Expected YYYY-YYYY")
    
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise ValueError(f"Start year {start} must be <= end year {end}")
    
    return start, end
