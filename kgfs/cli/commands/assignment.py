"""Assignment working-set command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.workflows.assignments import assignment_working_set


def register(app: typer.Typer) -> None:
    app.command("assignment", help="Build a local assignment working set.")(assignment_cmd)


def assignment_cmd(
    topic: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum results."),
    create_collection: str | None = typer.Option(None, "--create-collection", help="Create a collection from results."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        report = assignment_working_set(conn, topic, config, limit=limit, create_collection_name=create_collection)
        console.print("[bold]Assignment Working Set[/bold]")
        print_results(f"Assignment: {topic}", report.results)
        _print_categories(report.categories)
        if report.citations:
            console.print("[bold]Local Citations[/bold]")
            console.print(report.citations)
        if report.collection_name:
            console.print(f"Created collection: {report.collection_name}")
        table = Table(title="Suggested Next Actions")
        table.add_column("Action")
        for action in report.next_actions:
            table.add_row(action)
        console.print(table)
    finally:
        conn.close()


def _print_categories(categories) -> None:
    table = Table(title="Categories")
    table.add_column("Category")
    table.add_column("Files")
    for category, results in categories.items():
        table.add_row(category, ", ".join(result.file_name for result in results))
    console.print(table)
