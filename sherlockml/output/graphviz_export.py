"""Graphviz DOT export for social networks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx


class GraphvizExporter:
    """DOT format export for social networks.
    
    Exports NetworkX graphs to Graphviz DOT format with
    platform-specific styling and colors.
    
    Example:
        >>> exporter = GraphvizExporter()
        >>> exporter.export(graph, Path("social_network.dot"))
        >>> # Convert to image: dot -Tpng social_network.dot -o network.png
    """
    
    # Platform colors for visual distinction
    PLATFORM_COLORS = {
        "github": "#24292e",
        "twitter": "#1da1f2",
        "linkedin": "#0077b5",
        "instagram": "#e1306c",
        "facebook": "#1877f2",
        "mastodon": "#6364ff",
        "reddit": "#ff4500",
        "youtube": "#ff0000",
        "twitch": "#9146ff",
        "discord": "#5865f2",
        "keybase": "#33a0ff",
        "hackernews": "#ff6600",
        "gitlab": "#fc6d26",
        "pastebin": "#02456c",
    }
    
    DEFAULT_COLOR = "#888888"
    
    def __init__(
        self,
        rankdir: str = "LR",
        node_shape: str = "box",
        font_name: str = "Helvetica",
    ):
        """Initialize the exporter.
        
        Args:
            rankdir: Graph direction (LR, TB, etc.)
            node_shape: Default node shape
            font_name: Font for labels
        """
        self.rankdir = rankdir
        self.node_shape = node_shape
        self.font_name = font_name
    
    def export(
        self,
        graph: "nx.DiGraph",
        output: Path | str | None = None,
        title: str = "Social Network Graph",
    ) -> str:
        """Export NetworkX graph to Graphviz DOT.

        Args:
            graph: NetworkX graph to export
            output: Output file path.  When None, the DOT string is built
                and returned without writing to disk.
            title: Graph title

        Returns:
            DOT format string
        """
        safe_title = self._escape_dot_text(title)
        lines = [
            "digraph SocialNetwork {",
            f'  label="{safe_title}";',
            f'  rankdir={self.rankdir};',
            f'  fontname="{self.font_name}";',
            f'  node [shape={self.node_shape}, style=filled, fontname="{self.font_name}"];',
            f'  edge [fontname="{self.font_name}"];',
            "",
        ]

        # Add nodes
        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]
            platform = node_data.get("platform", "unknown")
            username = node_data.get("username", str(node_id))

            color = self.PLATFORM_COLORS.get(platform.lower(), self.DEFAULT_COLOR)

            # Escape special characters (each field separately so the
            # literal "\n" line break below is preserved).
            label = f"{self._escape_dot_text(username)}\\n({self._escape_dot_text(platform)})"
            escaped_id = self._escape_dot_id(node_id)

            lines.append(
                f'  "{escaped_id}" [label="{label}", '
                f'fillcolor="{color}", fontcolor="white"];'
            )

        lines.append("")

        # Add edges
        for source, target, data in graph.edges(data=True):
            relationship = data.get("relationship", "")
            escaped_source = self._escape_dot_id(source)
            escaped_target = self._escape_dot_id(target)

            style = "solid"
            if relationship == "same_username":
                style = "dashed"
            elif relationship == "potential":
                style = "dotted"

            edge_label = ""
            if relationship and relationship not in ("linked", "same_username"):
                edge_label = f'label="{self._escape_dot_text(relationship)}", '

            lines.append(f'  "{escaped_source}" -> "{escaped_target}" [{edge_label}style={style}];')

        lines.append("}")

        dot_content = "\n".join(lines)

        # Write to file when a destination was given
        if output is not None:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(dot_content)

        return dot_content

    @staticmethod
    def _escape_dot_text(value: str) -> str:
        """Escape backslashes and double-quotes for a DOT string literal.

        Backslashes are escaped first so that quotes escaped afterwards are
        not re-processed (the previous order produced ``\\\\"`` from a single
        quote, breaking the string).
        """
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    def _escape_dot_id(self, node_id: str) -> str:
        """Escape special characters in DOT node IDs."""
        return self._escape_dot_text(node_id)
    
    def export_subgraph(
        self,
        graph: "nx.DiGraph",
        center_node: str,
        depth: int = 2,
        output: Path | str | None = None,
    ) -> str:
        """Export a subgraph centered on a specific node.
        
        Args:
            graph: Full graph
            center_node: Node to center on
            depth: How many hops from center to include
            output: Optional output path
            
        Returns:
            DOT format string
        """
        # Get nodes within depth
        nodes = {center_node}
        frontier = {center_node}
        
        for _ in range(depth):
            new_frontier = set()
            for node in frontier:
                # Get neighbors in both directions
                new_frontier.update(graph.predecessors(node))
                new_frontier.update(graph.successors(node))
            nodes.update(new_frontier)
            frontier = new_frontier
        
        # Create subgraph
        subgraph = graph.subgraph(nodes).copy()

        # export() skips the file write when output is None.
        return self.export(subgraph, output, title=f"Network around {center_node}")
    
    ALLOWED_FORMATS = {"png", "svg", "pdf", "ps", "eps", "json"}

    def render_to_image(
        self,
        dot_path: Path | str,
        output_path: Path | str,
        format: str = "png",
    ) -> bool:
        """Render DOT file to image using graphviz.

        Requires graphviz to be installed on the system.

        Args:
            dot_path: Path to .dot file
            output_path: Path for output image
            format: Output format (png, svg, pdf)

        Returns:
            True if successful

        Raises:
            ValueError: If format is not in ALLOWED_FORMATS
        """
        import subprocess

        if format not in self.ALLOWED_FORMATS:
            raise ValueError(
                f"Unsupported format {format!r}, must be one of {sorted(self.ALLOWED_FORMATS)}"
            )

        try:
            subprocess.run(
                ["dot", f"-T{format}", str(Path(dot_path).resolve()), "-o", str(Path(output_path).resolve())],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
