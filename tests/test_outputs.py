"""Tests for the Graphviz and Markdown outputs and lazy ML imports."""

import subprocess
import sys

import networkx as nx

from sherlockml.enum.orchestrator import SearchResult, SearchResults
from sherlockml.output.graphviz_export import GraphvizExporter
from sherlockml.output.markdown_writer import MarkdownWriter


class TestDotEscaping:
    def test_quote_escaped_once(self):
        assert GraphvizExporter()._escape_dot_id('a"b') == 'a\\"b'

    def test_backslash_then_quote(self):
        assert GraphvizExporter()._escape_dot_id('a\\"b') == 'a\\\\\\"b'

    def test_label_escapes_username(self, tmp_path):
        graph = nx.DiGraph()
        graph.add_node('x:evil"name', platform="x", username='evil"name')
        dot = GraphvizExporter().export(graph, tmp_path / "g.dot")
        assert 'label="evil\\"name\\n(x)"' in dot


class TestMarkdownWriter:
    def test_contacts_and_version_rendered(self):
        from sherlockml import __version__

        results = SearchResults(query_username="alice")
        results.results = [SearchResult(
            username="alice", platform="github", exists=True,
            url="https://github.com/alice",
            metadata={"_raw_response": "<html>secret</html>"},
        )]
        results.contacts = ["alice@proton.me"]
        md = MarkdownWriter().generate_writeup(results)
        assert "## Contacts" in md
        assert "alice@proton.me" in md
        assert f"SherlockML v{__version__}" in md
        assert "secret" not in md


def test_rl_controller_imports_without_heavy_ml_deps():
    """Importing RLController must not pull in chromadb / spaCy."""
    code = (
        "import sys\n"
        "from sherlockml.ml import RLController\n"
        "assert 'chromadb' not in sys.modules\n"
        "assert 'spacy' not in sys.modules\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
