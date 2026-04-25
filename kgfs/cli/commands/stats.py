"""Stats command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, format_bytes
from kgfs.db import get_database_stats


def register(app: typer.Typer) -> None:
    app.command()(stats)


def stats(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show index statistics."""

    _, _, resolved_database_path, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        stats_data = get_database_stats(conn, resolved_database_path)
    finally:
        conn.close()
    table = Table(title="KGFS Stats")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Total indexed files", str(stats_data["total_files"]))
    table.add_row("Total indexed folders", str(stats_data["total_folders"]))
    table.add_row("Total indexed size", format_bytes(stats_data["total_size"]))
    table.add_row("Extracted text size", format_bytes(stats_data["total_extracted_text_size"]))
    table.add_row("Last indexed time", str(stats_data["last_indexed"]))
    table.add_row("Semantic chunks", str(stats_data["total_chunks"]))
    table.add_row("Embedding storage", format_bytes(stats_data["embedding_bytes"]))
    table.add_row("Extraction successes", str(stats_data["extraction_successes"]))
    table.add_row("Extraction failures", str(stats_data["extraction_failures"]))
    table.add_row("Stale records", str(stats_data["stale_records"]))
    table.add_row("Database size", format_bytes(stats_data["database_size"]))
    table.add_row("Schema version", str(stats_data["schema_version"]))
    console.print(table)

    types_table = Table(title="File Types")
    types_table.add_column("Extension")
    types_table.add_column("Count", justify="right")
    for extension, count in stats_data["file_types"]:
        types_table.add_row(extension or "(none)", str(count))
    console.print(types_table)

    largest_table = Table(title="Largest Indexed Files")
    largest_table.add_column("Name")
    largest_table.add_column("Size", justify="right")
    largest_table.add_column("Path")
    for name, path, size in stats_data["largest_files"]:
        largest_table.add_row(name, format_bytes(size), path)
    console.print(largest_table)
