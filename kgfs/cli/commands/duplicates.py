"""Duplicate detection commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_bytes, format_timestamp
from kgfs.intelligence.duplicates import find_exact_duplicates, find_semantic_duplicates


def register(app: typer.Typer) -> None:
    app.command("duplicates", help="Find exact or semantic duplicate indexed files.")(duplicates_cmd)


def duplicates_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    exact: bool = typer.Option(False, "--exact", help="Find exact duplicates by content hash."),
    semantic: bool = typer.Option(False, "--semantic", help="Find semantic near-duplicates using local vectors."),
    min_score: float | None = typer.Option(None, "--min-score", help="Semantic duplicate threshold."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        report = (
            find_semantic_duplicates(conn, config, min_score=min_score)
            if semantic and not exact
            else find_exact_duplicates(conn)
        )
        table = Table(title="Duplicate Files")
        table.add_column("Group")
        table.add_column("Kind")
        table.add_column("Score")
        table.add_column("File")
        table.add_column("Size")
        table.add_column("Modified")
        table.add_column("Path")
        for group in report.groups:
            for item in group.items:
                table.add_row(
                    str(group.group_id),
                    group.kind,
                    f"{group.score:.3f}",
                    item.file_name,
                    format_bytes(item.size),
                    format_timestamp(item.modified_time),
                    str(item.path),
                )
        console.print(table)
        if not report.groups:
            console.print("No duplicate groups found.")
        for warning in report.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
    finally:
        conn.close()
