"""On-demand local file/topic graph building."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kgfs.core.config import KGFSConfig
from kgfs.db.latest_results import get_latest_result_record
from kgfs.intelligence.models import GraphEdge, GraphNode, GraphResult
from kgfs.search import search


def build_topic_graph(conn: sqlite3.Connection, query: str, config: KGFSConfig) -> GraphResult:
    nodes: list[GraphNode] = [GraphNode(id=f"topic:{query}", type="topic", label=query)]
    edges: list[GraphEdge] = []
    results = search(conn, query, limit=config.intelligence.graph_max_nodes)
    file_ids: list[int] = []
    for result in results:
        node_id = _file_node_id(result.file_id)
        nodes.append(
            GraphNode(
                id=node_id,
                type="file",
                label=result.file_name,
                file_id=result.file_id,
                metadata={"path": str(result.path), "score": result.score},
            )
        )
        edges.append(
            GraphEdge(source=f"topic:{query}", target=node_id, type="mentioned_by_search", weight=result.score)
        )
        file_ids.append(result.file_id)
    _add_metadata_edges(conn, nodes, edges, file_ids)
    return _bounded(GraphResult(query=query, nodes=nodes, edges=edges), config)


def build_file_graph(conn: sqlite3.Connection, result_id: int, config: KGFSConfig) -> GraphResult:
    latest = get_latest_result_record(conn, result_id)
    if latest is None:
        raise ValueError(f"No latest search result found for ID {result_id}. Run kgfs search first.")
    row = _file_row(conn, latest.file_id)
    node = GraphNode(
        id=_file_node_id(latest.file_id),
        type="file",
        label=row["file_name"],
        file_id=latest.file_id,
        metadata={"path": row["path"]},
    )
    nodes = [node]
    edges: list[GraphEdge] = []
    _add_same_folder_edges(conn, nodes, edges, latest.file_id)
    _add_metadata_edges(conn, nodes, edges, [latest.file_id])
    return _bounded(GraphResult(query=row["file_name"], nodes=nodes, edges=edges), config)


def build_project_graph(conn: sqlite3.Connection, name: str, config: KGFSConfig) -> GraphResult:
    project = conn.execute("SELECT id, name FROM projects WHERE name = ?", (name,)).fetchone()
    if project is None:
        raise ValueError(f"Unknown project: {name}")
    project_node_id = f"project:{project['id']}"
    nodes = [GraphNode(id=project_node_id, type="project", label=project["name"])]
    edges: list[GraphEdge] = []
    rows = conn.execute(
        """
        SELECT f.id, f.file_name, f.path
        FROM project_items pi
        JOIN files f ON f.id = pi.file_id
        WHERE pi.project_id = ?
        ORDER BY f.file_name
        """,
        (project["id"],),
    ).fetchall()
    file_ids = []
    for row in rows:
        node_id = _file_node_id(int(row["id"]))
        nodes.append(
            GraphNode(
                id=node_id, type="file", label=row["file_name"], file_id=int(row["id"]), metadata={"path": row["path"]}
            )
        )
        edges.append(GraphEdge(source=project_node_id, target=node_id, type="in_project", weight=1.0))
        file_ids.append(int(row["id"]))
    _add_metadata_edges(conn, nodes, edges, file_ids)
    return _bounded(GraphResult(query=name, nodes=nodes, edges=edges), config)


def export_graph_markdown(graph: GraphResult) -> str:
    title = graph.query or "KGFS Graph"
    lines = [f"# KGFS Graph: {title}", "", "## Nodes"]
    for node in graph.nodes:
        lines.append(f"- `{node.type}` {node.label}")
    lines.extend(["", "## Edges"])
    for edge in graph.edges:
        lines.append(f"- {edge.source} -> {edge.target} ({edge.type}, {edge.weight:.3f})")
    return "\n".join(lines) + "\n"


def _file_node_id(file_id: int) -> str:
    return f"file:{file_id}"


def _file_row(conn: sqlite3.Connection, file_id: int):
    row = conn.execute("SELECT id, file_name, path FROM files WHERE id = ?", (file_id,)).fetchone()
    if row is None:
        raise ValueError(f"File record {file_id} no longer exists in the KGFS index.")
    return row


def _add_metadata_edges(
    conn: sqlite3.Connection, nodes: list[GraphNode], edges: list[GraphEdge], file_ids: list[int]
) -> None:
    seen_nodes = {node.id for node in nodes}
    seen_edges = {(edge.source, edge.target, edge.type) for edge in edges}
    for file_id in file_ids:
        file_node = _file_node_id(file_id)
        for row in conn.execute(
            """
            SELECT t.id, t.name
            FROM file_tags ft
            JOIN tags t ON t.id = ft.tag_id
            WHERE ft.file_id = ?
            """,
            (file_id,),
        ).fetchall():
            _add_node(nodes, seen_nodes, GraphNode(id=f"tag:{row['id']}", type="tag", label=row["name"]))
            _add_edge(
                edges,
                seen_edges,
                GraphEdge(source=file_node, target=f"tag:{row['id']}", type="tagged_with", weight=1.0),
            )
        for row in conn.execute(
            """
            SELECT c.id, c.name
            FROM collection_items ci
            JOIN collections c ON c.id = ci.collection_id
            WHERE ci.file_id = ?
            """,
            (file_id,),
        ).fetchall():
            _add_node(nodes, seen_nodes, GraphNode(id=f"collection:{row['id']}", type="collection", label=row["name"]))
            _add_edge(
                edges,
                seen_edges,
                GraphEdge(source=file_node, target=f"collection:{row['id']}", type="in_collection", weight=1.0),
            )
        for row in conn.execute(
            """
            SELECT p.id, p.name
            FROM project_items pi
            JOIN projects p ON p.id = pi.project_id
            WHERE pi.file_id = ?
            """,
            (file_id,),
        ).fetchall():
            _add_node(nodes, seen_nodes, GraphNode(id=f"project:{row['id']}", type="project", label=row["name"]))
            _add_edge(
                edges,
                seen_edges,
                GraphEdge(source=file_node, target=f"project:{row['id']}", type="in_project", weight=1.0),
            )


def _add_same_folder_edges(
    conn: sqlite3.Connection, nodes: list[GraphNode], edges: list[GraphEdge], file_id: int
) -> None:
    row = _file_row(conn, file_id)
    folder = str(Path(row["path"]).parent)
    seen_nodes = {node.id for node in nodes}
    seen_edges = {(edge.source, edge.target, edge.type) for edge in edges}
    for candidate in conn.execute("SELECT id, file_name, path FROM files WHERE id != ?", (file_id,)).fetchall():
        if str(Path(candidate["path"]).parent) != folder:
            continue
        node_id = _file_node_id(int(candidate["id"]))
        _add_node(
            nodes,
            seen_nodes,
            GraphNode(
                id=node_id,
                type="file",
                label=candidate["file_name"],
                file_id=int(candidate["id"]),
                metadata={"path": candidate["path"]},
            ),
        )
        _add_edge(
            edges, seen_edges, GraphEdge(source=_file_node_id(file_id), target=node_id, type="same_folder", weight=0.6)
        )


def _add_node(nodes: list[GraphNode], seen: set[str], node: GraphNode) -> None:
    if node.id not in seen:
        nodes.append(node)
        seen.add(node.id)


def _add_edge(edges: list[GraphEdge], seen: set[tuple[str, str, str]], edge: GraphEdge) -> None:
    key = (edge.source, edge.target, edge.type)
    if key not in seen:
        edges.append(edge)
        seen.add(key)


def _bounded(graph: GraphResult, config: KGFSConfig) -> GraphResult:
    allowed_nodes = graph.nodes[: config.intelligence.graph_max_nodes]
    allowed_ids = {node.id for node in allowed_nodes}
    allowed_edges = [edge for edge in graph.edges if edge.source in allowed_ids and edge.target in allowed_ids][
        : config.intelligence.graph_max_edges
    ]
    warnings = list(graph.warnings)
    if len(graph.nodes) > len(allowed_nodes) or len(graph.edges) > len(allowed_edges):
        warnings.append("Graph was limited by intelligence.graph_max_nodes/graph_max_edges.")
    return GraphResult(query=graph.query, nodes=allowed_nodes, edges=allowed_edges, warnings=warnings)
