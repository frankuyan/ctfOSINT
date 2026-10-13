"""Tests for discovery provenance, evidence capture and graph export.

All searches run offline against StubPlatform (see conftest.py).
"""

import hashlib
import json
from unittest.mock import MagicMock, patch

import networkx as nx
import pytest
from click.testing import CliRunner

from sherlockml.cli import main
from sherlockml.config import Config
from sherlockml.enum.orchestrator import Orchestrator
from sherlockml.output.evidence import EvidenceWriter, _safe_name
from sherlockml.output.graph_builder import build_search_graph, export_graph

ALICE_PAGE = (
    "<html><body><h1>alice</h1>"
    '<a href="https://github.com/bobby">my code</a>'
    '<a href="https://twitter.com/ghosty">old account</a>'
    "</body></html>"
)


@pytest.fixture
def platforms(stub_platform):
    # "web" serves HTML pages; "api" behaves like a JSON-API platform
    # (no raw page body, just metadata) and only knows alice.
    web = stub_platform(
        name="web",
        pages={"alice": ALICE_PAGE, "bobby": "<html>bobby page</html>"},
    )
    api = stub_platform(name="api", pages={"alice": None}, metadata={"followers": 3})
    return [web, api]


async def _deep_search(platforms, **kwargs):
    return await Orchestrator(Config()).search(
        ["alice"], platforms, discover=True, max_hops=1, retain_raw=True, **kwargs,
    )


class TestProvenance:
    async def test_discovered_results_record_hop_and_source(self, platforms):
        results = await _deep_search(platforms)
        bobby = [r for r in results.found_results if r.username == "bobby"]
        assert len(bobby) == 1
        assert bobby[0].hop == 1
        assert bobby[0].discovered_from == "web:alice"

    async def test_seed_results_have_no_source(self, platforms):
        results = await _deep_search(platforms)
        alice = [r for r in results.found_results if r.username == "alice"]
        assert alice and all(r.hop == 0 and r.discovered_from is None for r in alice)

    async def test_discoveries_listed_in_sorted_order(self, platforms):
        results = await _deep_search(platforms)
        assert [d["username"] for d in results.discoveries] == ["bobby", "ghosty"]
        assert all(d["source"] == "web:alice" for d in results.discoveries)

    async def test_checked_at_is_utc_iso(self, platforms):
        results = await _deep_search(platforms)
        assert all(r.checked_at.endswith("Z") for r in results.results)

    async def test_json_report_carries_provenance(self, platforms):
        from sherlockml.output.json_reporter import JSONReporter

        report = JSONReporter().generate_report(await _deep_search(platforms))
        bobby = next(e for e in report["results"] if e["username"] == "bobby")
        assert bobby["hop"] == 1 and bobby["discovered_from"] == "web:alice"
        assert report["discoveries"][0]["username"] == "bobby"


class TestEvidenceWriter:
    async def test_writes_artifacts_and_valid_hashes(self, platforms, tmp_path):
        results = await _deep_search(platforms)
        case_dir = EvidenceWriter(tmp_path).write(results, proxy_used=True)

        manifest = json.loads((case_dir / "manifest.json").read_text())
        assert manifest["target"] == "alice"
        assert manifest["proxy_used"] is True
        assert len(manifest["items"]) == len(results.found_results)

        for item in manifest["items"]:
            data = (case_dir / item["file"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == item["sha256"]
            assert item["size_bytes"] == len(data)
            assert item["captured_at"].endswith("Z")

    async def test_html_saved_for_pages_json_for_api(self, platforms, tmp_path):
        results = await _deep_search(platforms)
        case_dir = EvidenceWriter(tmp_path).write(results)
        items = json.loads((case_dir / "manifest.json").read_text())["items"]
        by_key = {(i["platform"], i["username"]): i for i in items}

        web = by_key[("web", "alice")]
        assert web["content_type"] == "text/html"
        assert (case_dir / web["file"]).read_text() == ALICE_PAGE

        api = by_key[("api", "alice")]
        assert api["content_type"] == "application/json"
        observed = json.loads((case_dir / api["file"]).read_text())
        assert observed["metadata"]["followers"] == 3

    async def test_sha256sums_covers_every_file(self, platforms, tmp_path):
        results = await _deep_search(platforms)
        case_dir = EvidenceWriter(tmp_path).write(results)
        lines = (case_dir / "SHA256SUMS").read_text().splitlines()
        listed = {}
        for line in lines:
            digest, name = line.split("  ", 1)
            listed[name] = digest
        on_disk = {p.name for p in case_dir.iterdir() if p.name != "SHA256SUMS"}
        assert set(listed) == on_disk
        for name, digest in listed.items():
            assert hashlib.sha256((case_dir / name).read_bytes()).hexdigest() == digest

    async def test_runs_never_overwrite(self, platforms, tmp_path):
        results = await _deep_search(platforms)
        first = EvidenceWriter(tmp_path).write(results)
        second = EvidenceWriter(tmp_path).write(results)
        assert first != second and first.exists() and second.exists()

    def test_safe_name_blocks_traversal(self):
        assert "/" not in _safe_name("../../etc/passwd")
        assert not _safe_name("../../etc/passwd").startswith(".")
        assert _safe_name("") == "unknown"


class TestGraph:
    async def test_graph_structure(self, platforms):
        graph = build_search_graph(await _deep_search(platforms))
        assert graph.has_edge("user:alice", "web:alice")
        assert graph.has_edge("user:alice", "api:alice")
        assert graph.has_edge("web:alice", "user:bobby")
        assert graph.has_edge("user:bobby", "web:bobby")
        # Linked from alice's page but never found anywhere: still a lead
        assert graph.has_edge("web:alice", "user:ghosty")
        assert graph.out_degree("user:ghosty") == 0

    async def test_graphml_roundtrip(self, platforms, tmp_path):
        path = tmp_path / "g.graphml"
        assert export_graph(await _deep_search(platforms), path) == path
        loaded = nx.read_graphml(path)
        assert loaded.has_edge("web:alice", "user:bobby")

    async def test_dot_export(self, platforms, tmp_path):
        path = tmp_path / "g.dot"
        export_graph(await _deep_search(platforms), path)
        dot = path.read_text()
        assert '"web:alice" -> "user:bobby"' in dot
        assert "shape=ellipse" in dot

    async def test_render_falls_back_to_dot(self, platforms, tmp_path):
        path = tmp_path / "g.svg"
        with patch(
            "sherlockml.output.graph_builder.GraphvizExporter.render_to_image",
            return_value=False,
        ):
            written = export_graph(await _deep_search(platforms), path)
        assert written == tmp_path / "g.dot" and written.exists()


class TestSearchCommand:
    def test_evidence_and_graph_from_cli(self, platforms, tmp_path):
        registry = MagicMock()
        registry.get_enabled.return_value = platforms
        evidence = tmp_path / "cases"
        graph = tmp_path / "graph.graphml"
        with patch("sherlockml.cli.load_config", return_value=Config()), \
             patch("sherlockml.enum.registry.get_registry", return_value=registry):
            result = CliRunner().invoke(main, [
                "search", "alice", "--no-variants", "--deep", "--max-hops", "1",
                "--evidence-dir", str(evidence), "--graph", str(graph),
                "-o", str(tmp_path / "report"),
            ])
        assert result.exit_code == 0, result.output
        assert "via web:alice" in result.output

        (case_dir,) = list(evidence.iterdir())
        assert (case_dir / "SHA256SUMS").exists()
        assert nx.read_graphml(graph).has_edge("web:alice", "user:bobby")

        # Captured pages went to the evidence folder, not the JSON report
        report = json.loads((tmp_path / "report.json").read_text())
        assert all("_raw_response" not in e.get("metadata", {}) for e in report["results"])
