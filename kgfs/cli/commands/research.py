"""Local research mode command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.search.filters import SearchFilters
from kgfs.search.research import research_query


def register(app: typer.Typer) -> None:
    app.command("research")(research_cmd)


def research_cmd(
    query: str = typer.Argument(..., help="Research question to investigate locally."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum local files to include."),
    mode: str | None = typer.Option(None, "--mode", help="Search mode: auto, keyword, semantic, or hybrid."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Filter by extension, e.g. --ext .pdf."),
    folder: str | None = typer.Option(None, "--folder", help="Filter by folder/path substring."),
    after: str | None = typer.Option(None, "--after", help="Only files modified on/after YYYY-MM-DD."),
    before: str | None = typer.Option(None, "--before", help="Only files modified on/before YYYY-MM-DD."),
) -> None:
    """Build a local citation-backed research brief without AI."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        filters = SearchFilters(extensions=ext, folder=folder, after=after, before=before)
        report = research_query(conn, query, config, limit=limit, mode=mode, filters=filters)
        for warning in report.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        console.print("[bold]Research Brief[/bold]")
        print_results(f"Research: {query}", report.results)
        if report.citations:
            console.print("[bold]Local Citations[/bold]")
            console.print(report.citations)
        _print_list("Related Terms", report.related_terms)
        _print_list("Suggested Follow-ups", report.followups)
        _print_list("Gaps", report.gaps)
    finally:
        conn.close()


def _print_list(title: str, values: list[str]) -> None:
    if not values:
        return
    table = Table(title=title)
    table.add_column("Item")
    for value in values:
        table.add_row(value)
    console.print(table)
