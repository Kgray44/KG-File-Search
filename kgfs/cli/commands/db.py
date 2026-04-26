"""Database maintenance and release-readiness checks."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import console, optional_config_runtime
from kgfs.db.checks import check_database

db_app = typer.Typer(help="Inspect KGFS database integrity and metadata health.")


def register(app: typer.Typer) -> None:
    app.add_typer(db_app, name="db")


@db_app.command("check")
def db_check_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Run read-only SQLite integrity and metadata sanity checks."""

    _, _, resolved_database_path, config = optional_config_runtime(config_path, database_path, project_local)
    config = config.model_copy(update={"database_path": resolved_database_path})
    try:
        report = check_database(resolved_database_path, config)
    except FileNotFoundError as exc:
        console.print(str(exc))
        raise typer.Exit(code=2) from exc

    table = Table(title="KGFS Database Check")
    table.add_column("Check")
    table.add_column("Value")
    table.add_column("Details")
    table.add_row("SQLite integrity", report.integrity_check, str(report.database_path))
    table.add_row(
        "Schema version",
        str(report.schema_version),
        f"expected {report.expected_schema_version}",
    )
    table.add_row(
        "Foreign keys",
        "ok" if not report.foreign_key_violations else "failed",
        f"{len(report.foreign_key_violations)} violation(s)",
    )
    orphan_count = sum(report.orphaned_metadata.values())
    table.add_row(
        "Orphaned metadata",
        "ok" if orphan_count == 0 else "failed",
        f"{orphan_count} orphaned reference(s)",
    )
    table.add_row(
        "Artifact sanity",
        "ok" if report.artifact_sanity.startswith("ok") else "warning",
        report.artifact_sanity,
    )
    console.print(table)
    if report.orphaned_metadata:
        details = Table(title="Orphaned Metadata Details")
        details.add_column("Reference")
        details.add_column("Count", justify="right")
        for reference, count in sorted(report.orphaned_metadata.items()):
            details.add_row(reference, str(count))
        console.print(details)
    if report.foreign_key_violations:
        console.print("[yellow]Foreign key violations were reported by SQLite PRAGMA foreign_key_check.[/yellow]")
    if not report.ok:
        raise typer.Exit(code=1)
