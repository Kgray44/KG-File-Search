"""Timeline search command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_timestamp
from kgfs.search.filters import SearchFilters
from kgfs.search.timeline import timeline_search


def register(app: typer.Typer) -> None:
    app.command("timeline")(timeline_cmd)


def timeline_cmd(
    query: str = typer.Argument(..., help="Search query to place on a timeline."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum timeline results."),
    group: str = typer.Option("month", "--group", help="Group by day, month, or year."),
    mode: str | None = typer.Option(None, "--mode", help="Search mode: auto, keyword, semantic, or hybrid."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Filter by extension, e.g. --ext .pdf."),
    folder: str | None = typer.Option(None, "--folder", help="Filter by folder/path substring."),
    after: str | None = typer.Option(None, "--after", help="Only files modified on/after YYYY-MM-DD."),
    before: str | None = typer.Option(None, "--before", help="Only files modified on/before YYYY-MM-DD."),
) -> None:
    """Show matching files chronologically."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        filters = SearchFilters(extensions=ext, folder=folder, after=after, before=before)
        report = timeline_search(conn, query, config, limit=limit, group=group, mode=mode, filters=filters)
        for warning in report.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        _print_timeline(query, report.items)
    finally:
        conn.close()


def _print_timeline(query: str, items) -> None:
    table = Table(title=f"Timeline: {query}")
    table.add_column("ID", justify="right")
    table.add_column("When")
    table.add_column("Group")
    table.add_column("Name")
    table.add_column("Source")
    table.add_column("Snippet")
    for item in items:
        table.add_row(
            str(item.result_id),
            format_timestamp(item.modified_time),
            item.group,
            item.file_name,
            item.source,
            item.snippet,
        )
    console.print(table)
    if not items:
        console.print("No timeline results.")
