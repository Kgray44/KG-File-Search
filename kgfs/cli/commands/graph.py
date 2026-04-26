"""Local graph commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console
from kgfs.intelligence.graph import build_file_graph, build_project_graph, build_topic_graph, export_graph_markdown


def register(app: typer.Typer) -> None:
    app.command("graph", help="Explore a local KGFS file/topic graph.")(graph_cmd)
    app.command("graph-export", help="Export a local KGFS graph as Markdown.")(graph_export_cmd)


def graph_cmd(
    query: str | None = typer.Argument(None, help="Topic query for a graph."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    result_id: int | None = typer.Option(None, "--file", help="Build graph around a latest result ID."),
    project: str | None = typer.Option(None, "--project", help="Build graph around a project."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            if result_id is not None:
                graph = build_file_graph(conn, result_id, config)
            elif project:
                graph = build_project_graph(conn, project, config)
            else:
                graph = build_topic_graph(conn, query or "", config)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        _print_graph(graph)
    finally:
        conn.close()


def graph_export_cmd(
    query: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    format_name: str = typer.Option("markdown", "--format", help="Export format: markdown."),
) -> None:
    if format_name.lower() != "markdown":
        raise typer.BadParameter("Only markdown graph export is supported in this phase.")
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print(export_graph_markdown(build_topic_graph(conn, query, config)))
    finally:
        conn.close()


def _print_graph(graph) -> None:
    node_table = Table(title=f"Graph Nodes: {graph.query or ''}")
    node_table.add_column("Type")
    node_table.add_column("Label")
    for node in graph.nodes:
        node_table.add_row(node.type, node.label)
    console.print(node_table)
    edge_table = Table(title="Graph Edges")
    edge_table.add_column("Source")
    edge_table.add_column("Type")
    edge_table.add_column("Target")
    edge_table.add_column("Weight", justify="right")
    for edge in graph.edges:
        edge_table.add_row(edge.source, edge.type, edge.target, f"{edge.weight:.3f}")
    console.print(edge_table)
    for warning in graph.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
