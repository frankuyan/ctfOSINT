"""Tests for JSON reporter and confidence scoring."""

import pytest

from sherlockml.enum.orchestrator import SearchResult, SearchResults
from sherlockml.output.json_reporter import ConfidenceWeights, JSONReporter


def _make_result(platform: str, exists: bool, **kwargs) -> SearchResult:
    """Helper to create SearchResult instances."""
    return SearchResult(
        username="testuser",
        platform=platform,
        exists=exists,
        url=f"https://{platform}.com/testuser" if exists else None,
        confidence=kwargs.get("confidence", 0.0),
        response_time=kwargs.get("response_time", 0.5),
        metadata=kwargs.get("metadata", {}),
        error=kwargs.get("error"),
    )


def _make_results(results_list: list[SearchResult]) -> SearchResults:
    """Helper to create SearchResults."""
    return SearchResults(
        query_username="testuser",
        variants_searched=["testuser"],
        results=results_list,
        total_platforms=len(results_list),
        successful_checks=sum(1 for r in results_list if not r.error),
        found_count=sum(1 for r in results_list if r.exists),
        elapsed_time=1.5,
    )


class TestConfidenceWeights:
    """Test confidence weight defaults."""

    def test_defaults_sum_to_one(self):
        w = ConfidenceWeights()
        total = w.platform_reliability + w.pattern_matches + w.cross_platform_correlation
        assert abs(total - 1.0) < 0.01


class TestJSONReporter:
    """Test JSON reporter functionality."""

    @pytest.fixture
    def reporter(self):
        return JSONReporter()

    def test_calculate_confidence_known_platform(self, reporter):
        result = _make_result("github", True, metadata={"bio": "CTF player", "name": "John"})
        score = reporter.calculate_confidence(result)
        assert 0.0 <= score <= 1.0
        # GitHub is reliable, should score well
        assert score > 0.5

    def test_calculate_confidence_unknown_platform(self, reporter):
        result = _make_result("unknown_platform", True)
        score = reporter.calculate_confidence(result)
        assert 0.0 <= score <= 1.0

    def test_calculate_confidence_with_correlation(self, reporter):
        results = [
            _make_result("github", True),
            _make_result("twitter", True),
            _make_result("reddit", True),
        ]
        # Score with correlation should be higher
        score_with = reporter.calculate_confidence(results[0], results)
        score_without = reporter.calculate_confidence(results[0])
        assert score_with >= score_without

    def test_metadata_scoring_empty(self, reporter):
        score = reporter._score_metadata({})
        assert score == 0.3

    def test_metadata_scoring_rich(self, reporter):
        metadata = {
            "bio": "Security researcher",
            "email": "user@example.com",
            "location": "NYC",
            "name": "John Doe",
            "created_at": "2020-01-01",
            "followers": 100,
        }
        score = reporter._score_metadata(metadata)
        assert score > 0.8

    def test_generate_report_basic(self, reporter):
        results = _make_results([
            _make_result("github", True, metadata={"name": "Test"}),
            _make_result("twitter", False),
        ])
        report = reporter.generate_report(results)

        assert "sherlockml_version" in report
        assert "generated_at" in report
        assert "summary" in report
        assert report["summary"]["profiles_found"] == 1
        assert len(report["results"]) == 1  # Only found results by default

    def test_generate_report_include_negative(self, reporter):
        results = _make_results([
            _make_result("github", True),
            _make_result("twitter", False),
        ])
        report = reporter.generate_report(results, include_negative=True)
        assert len(report["results"]) == 2

    def test_generate_report_with_flags(self, reporter):
        results = _make_results([_make_result("github", True)])
        results.flags_found = ["flag{test123}"]
        report = reporter.generate_report(results)
        assert "flags" in report
        assert "flag{test123}" in report["flags"]

    def test_results_sorted_by_confidence(self, reporter):
        results = _make_results([
            _make_result("pastebin", True),  # Lower reliability
            _make_result("github", True, metadata={"name": "Test", "bio": "Bio"}),  # Higher
        ])
        report = reporter.generate_report(results)
        scores = [r["confidence_score"] for r in report["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_save_and_load(self, reporter, tmp_path):
        results = _make_results([_make_result("github", True)])
        report = reporter.generate_report(results)

        output = tmp_path / "report.json"
        reporter.save(report, output)

        assert output.exists()
        import json
        loaded = json.loads(output.read_text())
        assert loaded["summary"]["profiles_found"] == 1

    def test_to_json_string(self, reporter):
        results = _make_results([_make_result("github", True)])
        report = reporter.generate_report(results)
        json_str = reporter.to_json_string(report)
        assert isinstance(json_str, str)
        assert "github" in json_str


class TestReportCompleteness:
    """Contacts, verification and timestamps must reach the saved report."""

    @pytest.fixture
    def results(self):
        results = SearchResults(query_username="alice")
        results.results = [SearchResult(
            username="alice", platform="github", exists=True,
            url="https://github.com/alice",
            metadata={"bio": "hi", "_raw_response": "<html>secret</html>"},
        )]
        results.found_count = 1
        results.contacts = ["alice@proton.me"]
        return results

    def test_contacts_included(self, results):
        report = JSONReporter().generate_report(results)
        assert report["contacts"] == ["alice@proton.me"]

    def test_verification_included(self, results):
        from sherlockml.enum.verify import VerificationResult

        verdict = VerificationResult(
            platform="github", url="https://github.com/alice",
            verdict="real", confidence=0.9, reason="active account",
        )
        report = JSONReporter().generate_report(results, verification=[verdict])
        assert report["verification"][0]["verdict"] == "real"

    def test_generated_at_is_valid_utc_iso(self, results):
        from datetime import datetime

        stamp = JSONReporter().generate_report(results)["generated_at"]
        assert stamp.endswith("Z") and "+00:00" not in stamp
        assert datetime.fromisoformat(stamp).utcoffset().total_seconds() == 0

    def test_raw_response_excluded_by_default(self, results):
        report = JSONReporter().generate_report(results)
        assert "_raw_response" not in report["results"][0]["metadata"]
        assert report["results"][0]["metadata"]["bio"] == "hi"

    def test_raw_response_included_when_requested(self, results):
        report = JSONReporter(include_raw=True).generate_report(results)
        assert report["results"][0]["metadata"]["_raw_response"] == "<html>secret</html>"
