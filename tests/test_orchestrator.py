"""Tests for the orchestrator's URL / handle / email extraction logic.

These tests target the static extractor helpers directly so they don't
need a live HTTP session or full Config — they take a constructed
SearchResult and assert on what gets pulled out of its metadata.
"""

from sherlockml.enum.orchestrator import (
    Orchestrator,
    SearchResult,
    _SOCIAL_PATTERNS,
    _SKIP_USERNAMES,
)
from sherlockml.flags import compile_flag_patterns


def _result(raw: str = "", url: str | None = None, **meta) -> SearchResult:
    """Build a minimal SearchResult with the given raw HTML / extra metadata."""
    md = {"_raw_response": raw, **meta} if raw else dict(meta)
    return SearchResult(
        username="seed",
        platform="testplatform",
        exists=True,
        url=url,
        metadata=md,
    )


class TestSocialPatterns:
    """Per-platform URL patterns."""

    def test_github_extracts(self):
        r = _result("https://github.com/torvalds in the bio")
        assert "torvalds" in Orchestrator._extract_discovered_usernames(r)

    def test_dev_to_extracts(self):
        # This case was broken before commit 834b2f1 (the \\.com suffix
        # was applied to the whole alternation).
        r = _result("see https://dev.to/janedoe for posts")
        assert "janedoe" in Orchestrator._extract_discovered_usernames(r)

    def test_twitch_tv_extracts(self):
        r = _result("streaming at https://twitch.tv/streamer1")
        assert "streamer1" in Orchestrator._extract_discovered_usernames(r)

    def test_bsky_extracts(self):
        r = _result("https://bsky.app/profile/bob.bsky.social")
        assert "bob.bsky.social" in Orchestrator._extract_discovered_usernames(r)

    def test_news_ycombinator_extracts(self):
        r = _result("https://news.ycombinator.com/user?id=pg")
        assert "pg" in Orchestrator._extract_discovered_usernames(r)

    def test_telegram_extracts_both_domains(self):
        r1 = _result("https://t.me/durov")
        r2 = _result("https://telegram.me/durov")
        assert "durov" in Orchestrator._extract_discovered_usernames(r1)
        assert "durov" in Orchestrator._extract_discovered_usernames(r2)

    def test_telegram_invite_link_rejected(self):
        # Invite links (t.me/+...) shouldn't be treated as a username.
        r = _result("https://t.me/+joinlinkABCxyz")
        assert Orchestrator._extract_discovered_usernames(r) == set()

    def test_tiktok_extracts(self):
        r = _result("https://www.tiktok.com/@charlidamelio")
        assert "charlidamelio" in Orchestrator._extract_discovered_usernames(r)

    def test_steam_vanity_extracts_but_numeric_does_not(self):
        good = _result("https://steamcommunity.com/id/gabelogannewell")
        assert "gabelogannewell" in Orchestrator._extract_discovered_usernames(good)
        bad = _result("https://steamcommunity.com/profiles/76561197960287930")
        assert Orchestrator._extract_discovered_usernames(bad) == set()

    def test_tumblr_subdomain_form(self):
        r = _result("https://hannahdiamond.tumblr.com/")
        assert "hannahdiamond" in Orchestrator._extract_discovered_usernames(r)

    def test_tumblr_path_form(self):
        r = _result("https://tumblr.com/hannahdiamond")
        assert "hannahdiamond" in Orchestrator._extract_discovered_usernames(r)

    def test_lookalike_domain_rejected(self):
        # notgithub.com / faketumblr.com / box.com should not be matched
        # as github / tumblr / x.com (the original regex had this bug).
        for url in (
            "https://notgithub.com/somebody",
            "https://faketumblr.com/staff",
            "https://nottumblr.com/anyone",
            "https://box.com/notauser",
            "https://linux.com/articles/foo",
        ):
            r = _result(url)
            assert Orchestrator._extract_discovered_usernames(r) == set(), url

    def test_skip_list_filters_path_segments(self):
        # github.com/explore is a real URL but 'explore' is not a username.
        r = _result("see https://github.com/explore for trending")
        assert "explore" not in Orchestrator._extract_discovered_usernames(r)


class TestHandleMentions:
    """Bare @handle mentions in bios feed back as discovery seeds."""

    def test_bare_handle_extracted(self):
        r = _result("Follow me @alice_codes please")
        assert "alice_codes" in Orchestrator._extract_discovered_usernames(r)

    def test_email_local_not_extracted_as_handle(self):
        # alice@gmail.com — @gmail is preceded by 'e' (word char), so the
        # handle regex's lookbehind rejects it.
        r = _result("Email alice@gmail.com here")
        assert "gmail" not in Orchestrator._extract_discovered_usernames(r)

    def test_url_attached_handle_not_extracted(self):
        # x.com/@dave_x — @dave is preceded by '/'.
        r = _result("See https://x.com/@dave_x for more")
        out = Orchestrator._extract_discovered_usernames(r)
        # The x.com pattern still picks up 'dave_x' as a URL match — that's
        # fine. The @handle path should not also extract it.
        # Just verify the result is *some* form of dave_x and nothing weird.
        assert out == {"dave_x"} or out == set()

    def test_short_handle_rejected(self):
        r = _result("Skip @ab and @1abc (digit-led)")
        assert Orchestrator._extract_discovered_usernames(r) == set()


class TestContactExtraction:
    """Email harvesting is evidence-only, never fed back as a seed."""

    def test_basic_email_extracted(self):
        r = _result("Contact alice@protonmail.com please")
        assert "alice@protonmail.com" in Orchestrator._extract_contacts(r)

    def test_plus_tag_email(self):
        r = _result("alice.smith+ctf@gmail.com")
        assert "alice.smith+ctf@gmail.com" in Orchestrator._extract_contacts(r)

    def test_role_address_filtered(self):
        for noisy in (
            "noreply@github.com",
            "support@stripe.com",
            "donotreply@foo.com",
            "info@example.org",
            "webmaster@example.com",
        ):
            r = _result(f"contact {noisy}")
            assert Orchestrator._extract_contacts(r) == set(), noisy

    def test_one_letter_tld_rejected(self):
        r = _result("user@domain.x")
        assert Orchestrator._extract_contacts(r) == set()

    def test_mailto_link_works(self):
        r = _result('<a href="mailto:carol@uni.edu">Carol</a>')
        assert "carol@uni.edu" in Orchestrator._extract_contacts(r)

    def test_case_insensitive_dedup(self):
        r = _result("alice@PROTONMAIL.com and ALICE@protonmail.com")
        # Both lowercase to the same email
        assert Orchestrator._extract_contacts(r) == {"alice@protonmail.com"}


class TestCollectSearchableText:
    """The shared text-collection helper."""

    def test_includes_raw_response(self):
        r = _result("hello world")
        texts = Orchestrator._collect_searchable_text(r)
        assert "hello world" in texts

    def test_includes_url(self):
        r = _result("", url="https://example.com/foo")
        texts = Orchestrator._collect_searchable_text(r)
        assert "https://example.com/foo" in texts

    def test_includes_short_metadata_strings(self):
        r = _result("", bio="short bio")
        texts = Orchestrator._collect_searchable_text(r)
        assert "short bio" in texts

    def test_skips_long_metadata_strings(self):
        # 500+ char strings get skipped from the metadata scan to avoid
        # re-scanning the raw response that lives under _raw_response.
        long_val = "x" * 600
        r = _result("real raw", filler=long_val)
        texts = Orchestrator._collect_searchable_text(r)
        assert long_val not in texts


class TestSkipList:
    """The skip list should cover common non-username path segments."""

    def test_common_paths_in_skip_list(self):
        for needed in ("explore", "settings", "login", "search", "about",
                       "staff", "www", "ondemand"):
            assert needed in _SKIP_USERNAMES, needed

    def test_skip_list_is_lowercase(self):
        for entry in _SKIP_USERNAMES:
            assert entry == entry.lower()


class TestPatternCount:
    """Sanity check that the platform pattern set didn't shrink."""

    def test_at_least_25_platforms(self):
        assert len(_SOCIAL_PATTERNS) >= 25


class TestScanFlags:
    """Flag scanning must surface whole flags from URL and metadata."""

    def test_flag_in_raw_response(self):
        pats = compile_flag_patterns()
        r = _result("<p>the flag is flag{s3cr3t_v4lu3}</p>")
        assert Orchestrator._scan_flags(r, pats) == ["flag{s3cr3t_v4lu3}"]

    def test_flag_in_url(self):
        pats = compile_flag_patterns()
        r = _result(url="https://ctf.example/flag{url_flag}")
        assert "flag{url_flag}" in Orchestrator._scan_flags(r, pats)

    def test_flag_in_string_metadata(self):
        pats = compile_flag_patterns()
        r = _result(bio="my bio CTF{in_bio}")
        assert "CTF{in_bio}" in Orchestrator._scan_flags(r, pats)

    def test_deduplicates_within_result(self):
        pats = compile_flag_patterns()
        r = _result("flag{dup}", extra="flag{dup}")
        assert Orchestrator._scan_flags(r, pats) == ["flag{dup}"]

    def test_no_patterns_returns_empty(self):
        r = _result("flag{ignored}")
        assert Orchestrator._scan_flags(r, []) == []

    def test_no_flags_returns_empty(self):
        pats = compile_flag_patterns()
        r = _result("nothing interesting here")
        assert Orchestrator._scan_flags(r, pats) == []
