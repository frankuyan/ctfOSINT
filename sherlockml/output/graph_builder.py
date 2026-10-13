"""Build an investigation graph from search results.

Two kinds of node:

* identity nodes (``user:<name>``) — a username that was searched, either
  a seed/variant or one discovered by ``--deep``;
* profile nodes (``<platform>:<username>``) — an account that was found.

Edges are identity → profile ("has an account here", drawn dashed) and
profile → identity ("this profile linked to that username", drawn solid),
so the graph shows exactly which page led to each pivot.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import networkx as nx

from sherlockml.output.graphviz_export import GraphvizExporter

if TYPE_CHECKING:
    from sherlockml.enum.orchestrator import SearchResults

RENDER_FORMATS = {"svg", "png", "pdf"}


def _identity_id(username: str) -> str:
    return f"user:{username.lower()}"


def build_search_graph(results: SearchResults) -> nx.DiGraph:
    """Return a DiGraph of identities, found profiles and discovery links."""
    graph = nx.DiGraph()

    def add_identity(username: str, hop: int) -> str:
        node = _identity_id(username)
        if node not in graph:
            graph.add_node(
                node, kind="identity", platform="username",
                username=username, hop=hop, shape="ellipse",
            )
        return node

    for result in results.found_results:
        identity = add_identity(result.username, result.hop)
        graph.add_node(
            result.node_id, kind="profile", platform=result.platform,
            username=result.username, url=result.url or "",
            confidence=round(result.confidence, 3), hop=result.hop,
        )
        graph.add_edge(identity, result.node_id, relationship="same_username")

    # Discovered usernames are kept even if no account was found for them:
    # "linked but not found" is still a lead.
    for found in results.discoveries:
        identity = add_identity(found["username"], found["hop"])
        if found["source"] in graph:
            graph.add_edge(found["source"], identity, relationship="linked")

    return graph


def export_graph(results: SearchResults, path: Path) -> Path:
    """Write the investigation graph to ``path``; the suffix picks the format.

    ``.graphml`` → GraphML (Gephi, yEd, Cytoscape); ``.dot``/``.gv`` →
    Graphviz DOT; ``.svg``/``.png``/``.pdf`` → DOT rendered with the
    ``dot`` binary (the ``.dot`` source is kept next to it).

    Returns the path actually written (the ``.dot`` file if rendering
    failed because Graphviz isn't installed).
    """
    graph = build_search_graph(results)
    title = f"SherlockML: {results.query_username}"
    suffix = path.suffix.lower().lstrip(".")
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == "graphml":
        nx.write_graphml(graph, path)
        return path

    exporter = GraphvizExporter()
    if suffix in RENDER_FORMATS:
        dot_path = path.with_suffix(".dot")
        exporter.export(graph, dot_path, title=title)
        return path if exporter.render_to_image(dot_path, path, format=suffix) else dot_path

    exporter.export(graph, path, title=title)
    return path
