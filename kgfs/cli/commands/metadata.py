"""Workflow metadata backup/import commands."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import connect_runtime, console
from kgfs.intelligence.export import (
    create_metadata_backup,
    import_metadata,
    read_metadata_export,
    write_metadata_export,
)


metadata_app = typer.Typer(help="Export, import, backup, and restore local KGFS metadata.")


def register(app: typer.Typer) -> None:
    app.add_typer(metadata_app, name="metadata")


@metadata_app.command("export")
def metadata_export_cmd(
    output: Path = typer.Option(..., "--output", help="Output JSON backup path."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        summary = write_metadata_export(conn, output)
        console.print(f"Exported {summary.exported_items} metadata sections to {summary.path}.")
    finally:
        conn.close()


@metadata_app.command("import")
def metadata_import_cmd(
    input_path: Path,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    yes: bool = typer.Option(False, "--yes", help="Confirm KGFS metadata import."),
) -> None:
    if not yes and not typer.confirm("Import KGFS metadata into the local database?", default=False):
        console.print("Metadata import cancelled.")
        return
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        payload = read_metadata_export(input_path)
        summary = import_metadata(conn, payload, yes=True)
        console.print(f"Restored {summary.restored_items} metadata rows; unmatched {summary.unmatched_items}.")
        for warning in summary.warnings[:20]:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
    finally:
        conn.close()


@metadata_app.command("backup")
def metadata_backup_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    note: str | None = typer.Option(None, "--note", help="Optional backup note."),
) -> None:
    app_paths, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        summary = create_metadata_backup(conn, app_paths, config, note=note)
        console.print(f"Backed up KGFS metadata to {summary.path}.")
    finally:
        conn.close()


@metadata_app.command("restore")
def metadata_restore_cmd(
    backup_path: Path,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    yes: bool = typer.Option(False, "--yes", help="Confirm KGFS metadata restore."),
) -> None:
    metadata_import_cmd(
        backup_path,
        config_path=config_path,
        database_path=database_path,
        project_local=project_local,
        yes=yes,
    )
