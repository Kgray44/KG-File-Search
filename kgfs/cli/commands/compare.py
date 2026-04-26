"""Compare latest search results."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console
from kgfs.search.compare import compare_results


def register(app: typer.Typer) -> None:
    app.command("compare")(compare_cmd)


def compare_cmd(
    left_result_id: int = typer.Argument(..., help="First result ID from latest results."),
    right_result_id: int = typer.Argument(..., help="Second result ID from latest results."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Compare two saved KGFS result IDs locally."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            report = compare_results(conn, left_result_id, right_result_id, config)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print("[bold]Compare Results[/bold]")
        console.print(f"Left:  [{report.left.result_id}] {report.left.file_name}")
        console.print(f"Right: [{report.right.result_id}] {report.right.file_name}")
        console.print(f"Text similarity: {report.text_similarity:.3f}")
        if report.semantic_similarity is not None:
            console.print(f"Semantic similarity: {report.semantic_similarity:.3f}")
        _print_terms("Shared Terms", report.shared_terms)
        _print_terms(f"Unique to {report.left.file_name}", report.left_unique_terms)
        _print_terms(f"Unique to {report.right.file_name}", report.right_unique_terms)
        for note in report.notes:
            console.print(f"[yellow]Note:[/yellow] {note}")
    finally:
        conn.close()


def _print_terms(title: str, terms: list[str]) -> None:
    table = Table(title=title)
    table.add_column("Term")
    for term in terms:
        table.add_row(term)
    console.print(table)
