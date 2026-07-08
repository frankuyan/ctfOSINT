"""Tests for the Graphviz DOT exporter."""

import networkx as nx

from sherlockml.output.graphviz_export import GraphvizExporter


def _graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node("github:alice", platform="github", username="alice")
    g.add_node("twitter:alice", platform="twitter", username="alice")
    g.add_edge("github:alice", "twitter:alice", relationship="same_username")
    return g


class TestEscaping:
    def test_backslash_escaped_before_quote(self):
        # A single double-quote must become \" (not \\"), which requires
        # escaping backslashes before quotes.
        assert GraphvizExporter._escape_dot_text('git"hub') == 'git\\"hub'

    def test_backslash_doubled(self):
        assert GraphvizExporter._escape_dot_text("a\\b") == "a\\\\b"

    def test_quote_in_username_does_not_break_label(self):
        g = nx.DiGraph()
        g.add_node("x:weird", platform="twitter", username='we"ird')
        dot = GraphvizExporter().export(g)
        # The raw, unescaped sequence must not appear.
        assert 'we"ird' not in dot
        assert 'we\\"ird' in dot


class TestExport:
    def test_returns_dot_string(self):
        dot = GraphvizExporter().export(_graph())
        assert dot.startswith("digraph SocialNetwork {")
        assert dot.rstrip().endswith("}")
        assert "alice" in dot

    def test_no_output_does_not_write(self, tmp_path):
        # export() with output=None returns a string and writes nothing.
        before = set(tmp_path.iterdir())
        GraphvizExporter().export(_graph(), output=None)
        assert set(tmp_path.iterdir()) == before

    def test_writes_file_when_output_given(self, tmp_path):
        out = tmp_path / "graph.dot"
        GraphvizExporter().export(_graph(), output=out)
        assert out.exists()
        assert "digraph" in out.read_text()

    def test_export_subgraph_without_output(self):
        dot = GraphvizExporter().export_subgraph(_graph(), "github:alice", depth=1)
        assert "digraph" in dot

    def test_same_username_edge_is_dashed(self):
        dot = GraphvizExporter().export(_graph())
        assert "style=dashed" in dot


class TestRenderFormatValidation:
    def test_rejects_unknown_format(self, tmp_path):
        import pytest

        exporter = GraphvizExporter()
        with pytest.raises(ValueError):
            exporter.render_to_image(tmp_path / "x.dot", tmp_path / "x.gif", format="gif")
