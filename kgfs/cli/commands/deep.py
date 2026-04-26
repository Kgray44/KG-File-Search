"""Deep local search command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.search.deep import deep_search
from kgfs.search.filters import SearchFilters


def register(app: typer.Typer) -> None:
    app.command("deep")(deep_cmd)


def deep_cmd(
    query: str = typer.Argument(..., help="Question or topic to investigate locally."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum results."),
    mode: str | None = typer.Option(None, "--mode", help="Search mode: auto, keyword, semantic, or hybrid."),
    passes: int | None = typer.Option(None, "--passes", help="Maximum local query variants to run."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Filter by extension, e.g. --ext .pdf."),
    folder: str | None = typer.Option(None, "--folder", help="Filter by folder/path substring."),
    after: str | None = typer.Option(None, "--after", help="Only files modified on/after YYYY-MM-DD."),
    before: str | None = typer.Option(None, "--before", help="Only files modified on/before YYYY-MM-DD."),
) -> None:
    """Run deterministic multi-pass local search."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        if not config.deep_search.enabled:
            raise typer.BadParameter("Deep search is disabled by deep_search.enabled: false.")
        filters = SearchFilters(extensions=ext, folder=folder, after=after, before=before)
        report = deep_search(conn, query, config, limit=limit, mode=mode, passes=passes, filters=filters)
        for warning in report.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        console.print("[bold]Deep Search[/bold]")
        console.print("Query variants: " + ", ".join(report.variants))
        print_results(f"Deep Search: {query}", report.results)
        _print_followups(report.followups)
    finally:
        conn.close()


def _print_followups(followups: list[str]) -> None:
    if not followups:
        return
    table = Table(title="Suggested Follow-ups")
    table.add_column("Query")
    for item in followups:
        table.add_row(item)
    console.print(table)
