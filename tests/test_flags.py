"""Tests for the shared CTF flag extraction utilities."""

from sherlockml.flags import (
    DEFAULT_FLAG_PATTERNS,
    compile_flag_patterns,
    extract_flags,
)


class TestExtractFlags:
    """extract_flags must return whole flags, not just the prefix."""

    def test_returns_full_flag_not_prefix(self):
        # Regression: the default pattern's alternation used to be a
        # capturing group, so findall returned "flag" instead of the flag.
        pats = compile_flag_patterns()
        flags = extract_flags("here is flag{s3cr3t_v4lu3} ok", pats)
        assert "flag{s3cr3t_v4lu3}" in flags
        assert "flag" not in flags

    def test_multiple_formats(self):
        pats = compile_flag_patterns()
        text = "CTF{one} and picoCTF{two} and HTB{three}"
        flags = extract_flags(text, pats)
        assert "CTF{one}" in flags
        assert "picoCTF{two}" in flags
        assert "HTB{three}" in flags

    def test_case_insensitive(self):
        pats = compile_flag_patterns()
        flags = extract_flags("FLAG{upper} flag{lower}", pats)
        assert "FLAG{upper}" in flags
        assert "flag{lower}" in flags

    def test_user_supplied_capturing_group_still_full_match(self):
        # Even if the caller supplies a pattern with a capturing group,
        # extract_flags returns the entire match (group 0).
        pats = compile_flag_patterns([r"(myctf)\{[^}]+\}"])
        flags = extract_flags("payload myctf{deadbeef} tail", pats)
        assert flags == ["myctf{deadbeef}"]

    def test_no_match_returns_empty(self):
        pats = compile_flag_patterns()
        assert extract_flags("nothing to see here", pats) == []

    def test_empty_text_returns_empty(self):
        pats = compile_flag_patterns()
        assert extract_flags("", pats) == []


class TestCompileFlagPatterns:
    def test_defaults_when_none(self):
        assert compile_flag_patterns(None)
        assert len(compile_flag_patterns(None)) == len(DEFAULT_FLAG_PATTERNS)

    def test_defaults_when_empty(self):
        # An empty list falls back to the defaults.
        assert len(compile_flag_patterns([])) == len(DEFAULT_FLAG_PATTERNS)

    def test_custom_patterns_used(self):
        pats = compile_flag_patterns([r"X\{[^}]+\}"])
        assert len(pats) == 1
        assert extract_flags("X{y}", pats) == ["X{y}"]
