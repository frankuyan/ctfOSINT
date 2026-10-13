"""Untrusted text must be printed literally, never parsed as Rich markup.

Profile pages, archived snapshots, commit metadata and LLM summaries are
all controlled by the target.  Unescaped, a value like ``[/i]`` raises
``rich.errors.MarkupError`` after the scan already ran, and ``[red]...``
can spoof the tool's own output.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from sherlockml.cli import main
from sherlockml.config import Config
from sherlockml.enum.verify import VerificationResult, verify_profile
from sherlockml.extract.github_scanner import GitHubResult
from sherlockml.extract.wayback import WaybackDiff, WaybackResult, WaybackSnapshot

EVIL = "[/i]"          # unmatched closing tag: MarkupError if parsed
SPOOF = "[red]x[/red]"  # valid markup: would silently restyle if parsed


def _invoke(argv, config=None):
    with patch("sherlockml.cli.load_config", return_value=config or Config()):
        return CliRunner().invoke(main, argv)


def _assert_literal(result, *needles):
    assert result.exit_code == 0, f"{result.exception!r}\n{result.output}"
    for needle in needles:
        assert needle in result.output, needle


class TestSearchOutput:
    @pytest.fixture
    def registry(self, stub_platform):
        page = "<html>" + "profile text " * 80 + "</html>"
        platform = stub_platform(
            name="web",
            pages={"alice": page, "bob": page},
            bio=f"flag{{{EVIL}}}",
        )
        registry = MagicMock()
        registry.get_enabled.return_value = [platform]
        return registry

    def test_verification_tables_and_flags(self, registry, tmp_path):
        wordlist = tmp_path / "users.txt"
        wordlist.write_text("bob\n")
        config = Config()
        config.llm.api_key = "test-key"
        verdicts = [
            VerificationResult(
                platform="web", url="https://web.example/alice", verdict="real",
                confidence=0.9, reason="ok", display_name=SPOOF, bio=f"bio {EVIL}",
                join_date=EVIL, activity=EVIL, notable=EVIL, links=[f"https://x/{EVIL}"],
            ),
            VerificationResult(
                platform="web", url="https://web.example/bob", verdict="empty",
                confidence=0.8, reason=f"empty {EVIL}",
            ),
        ]
        with patch("sherlockml.enum.registry.get_registry", return_value=registry), \
             patch("sherlockml.enum.verify.verify_results", AsyncMock(return_value=verdicts)):
            result = _invoke(["search", "alice", "-w", str(wordlist), "--no-variants", "--verify"], config)
        _assert_literal(result, SPOOF, f"bio {EVIL}", f"empty {EVIL}", f"flag{{{EVIL}}}")


class TestWaybackOutput:
    def test_url_mode_diffs_and_endpoints(self):
        wb_result = WaybackResult(
            original_url=f"https://example.com/{EVIL}",
            snapshots=[WaybackSnapshot(
                url="u", timestamp="20240101000000",
                original_url="https://example.com", status_code=200, mime_type="text/html",
            )],
            hidden_endpoints=[f"/admin{EVIL}"],
            diffs=[WaybackDiff(
                old_timestamp="20230101000000", new_timestamp="20240101000000",
                added_lines=[f"added {EVIL}"], removed_lines=[f"removed {SPOOF}"],
            )],
            flags_found=[f"flag{{{EVIL}}}"],
        )
        with patch("sherlockml.extract.wayback.WaybackIntegration") as cls:
            cls.return_value.analyze_url = AsyncMock(return_value=wb_result)
            result = _invoke(["wayback", "https://example.com", "--diff"])
        _assert_literal(
            result, f"/admin{EVIL}", f"added {EVIL}", f"removed {SPOOF}", f"flag{{{EVIL}}}",
        )

    def test_domain_mode_urls(self):
        wb_result = WaybackResult(
            original_url="example.com",
            snapshots=[WaybackSnapshot(
                url="u", timestamp="20240101000000",
                original_url=f"https://example.com/{EVIL}", status_code=200,
                mime_type="text/html",
            )],
            hidden_endpoints=[f"https://example.com/.env{EVIL}"],
        )
        with patch("sherlockml.extract.wayback.WaybackIntegration") as cls:
            cls.return_value.scan_url_wildcard = AsyncMock(return_value=wb_result)
            result = _invoke(["wayback", f"example.com{EVIL}", "--mode", "domain"])
        _assert_literal(result, f"https://example.com/{EVIL}", f".env{EVIL}")


class TestScanGithubOutput:
    def test_commit_emails_and_flags(self):
        # Commit author emails are whatever the committer configured
        gh_result = GitHubResult(
            username="someone", profile_url="https://github.com/someone",
            emails_found=[f"{EVIL}@evil.example"], flags_found=[f"flag{{{SPOOF}}}"],
        )
        with patch("sherlockml.extract.github_scanner.GitHubScanner.scan_user",
                   AsyncMock(return_value=gh_result)):
            result = _invoke(["scan-github", "someone"])
        _assert_literal(result, f"{EVIL}@evil.example", f"flag{{{SPOOF}}}")


class TestVerificationFieldCoercion:
    """A prompt-injected page can steer the model's JSON field types."""

    async def _verify(self, llm_json):
        config = Config().llm
        config.api_key = "k"
        with patch("sherlockml.enum.verify._call_openai",
                   AsyncMock(return_value=json.dumps(llm_json))):
            return await verify_profile("web", "https://x", "alice", "<html/>", config, None)

    async def test_non_string_fields_become_text(self):
        v = await self._verify({
            "verdict": "REAL", "confidence": "high", "reason": None,
            "bio": {"nested": "object"}, "notable": ["a", "b"], "links": "https://one",
            "display_name": 42,
        })
        assert v.verdict == "real"
        assert v.confidence == 0.5
        assert v.reason == ""
        assert v.bio == '{"nested": "object"}'
        assert v.notable == '["a", "b"]'
        assert v.display_name == "42"
        assert v.links == ["https://one"]
        assert v.error is None

    async def test_unknown_verdict_and_out_of_range_confidence(self):
        v = await self._verify({"verdict": "definitely", "confidence": 7, "reason": "x"})
        assert v.verdict == "suspicious"
        assert v.confidence == 1.0

    async def test_non_object_response(self):
        v = await self._verify(["not", "an", "object"])
        assert v.verdict == "suspicious"
        assert v.error is None
