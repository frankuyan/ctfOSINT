"""Tests for flag extraction across scanners.

The default flag pattern has a capture group, so a naive ``re.findall``
returns ``"flag"`` instead of ``"flag{...}"``.  These tests pin the full
match being reported everywhere flags are scanned.
"""

from sherlockml.config import Config
from sherlockml.enum.orchestrator import Orchestrator
from sherlockml.enum.platform_base import BasePlatform, PlatformResult
from sherlockml.extract.wayback import WaybackIntegration, WaybackResult
from sherlockml.flags import DEFAULT_FLAG_PATTERNS, compile_flag_patterns, find_flags


class TestFindFlags:
    def test_returns_full_match_not_group(self):
        patterns = compile_flag_patterns(DEFAULT_FLAG_PATTERNS)
        assert find_flags("bio: flag{s3cr3t}", patterns) == ["flag{s3cr3t}"]

    def test_various_prefixes(self):
        patterns = compile_flag_patterns()
        text = "CTF{abc} picoCTF{xyz} HTB{123}"
        assert find_flags(text, patterns) == ["CTF{abc}", "picoCTF{xyz}", "HTB{123}"]

    def test_dedupes_across_overlapping_patterns(self):
        # FLAG{X} matches both default patterns (both are case-insensitive)
        patterns = compile_flag_patterns()
        assert find_flags("FLAG{X} and FLAG{X}", patterns) == ["FLAG{X}"]

    def test_custom_pattern(self):
        patterns = compile_flag_patterns([r"THM\{[^}]+\}"])
        assert find_flags("thm{lower} THM{upper}", patterns) == ["thm{lower}", "THM{upper}"]

    def test_no_match(self):
        assert find_flags("nothing here", compile_flag_patterns()) == []

    def test_config_defaults_match_module_defaults(self):
        assert Config().ctf.flag_patterns == list(DEFAULT_FLAG_PATTERNS)


class _StubPlatform(BasePlatform):
    """Platform that 'finds' every username and returns a canned bio."""

    name = "stub"
    display_name = "Stub"
    base_url = "https://stub.example"
    url_template = "https://stub.example/{username}"
    rate_limit_rpm = 6000.0

    def __init__(self, bio: str = "", raw: str | None = None):
        super().__init__()
        self.bio = bio
        self.raw = raw

    async def check_username(self, username, session):
        return PlatformResult(
            exists=True,
            url=self.get_url(username),
            metadata={"bio": self.bio},
            confidence=0.9,
            raw_response=self.raw,
        )


class TestOrchestratorFlags:
    async def test_search_reports_full_flags(self):
        platform = _StubPlatform(bio="hidden flag{in_the_bio} here")
        results = await Orchestrator(Config()).search(["alice"], [platform])
        assert results.flags_found == ["flag{in_the_bio}"]

    async def test_flags_deduplicated_across_results(self):
        platform = _StubPlatform(bio="flag{same}")
        results = await Orchestrator(Config()).search(["alice", "bob"], [platform])
        assert results.flags_found == ["flag{same}"]


class TestWaybackFlags:
    def test_add_flags_full_match_and_dedupe(self):
        result = WaybackResult(original_url="https://example.com")
        compiled = WaybackIntegration._compile_flag_patterns(None)
        WaybackIntegration._add_flags(result, "<p>flag{old_bio}</p>", compiled)
        WaybackIntegration._add_flags(result, "flag{old_bio} again", compiled)
        assert result.flags_found == ["flag{old_bio}"]
