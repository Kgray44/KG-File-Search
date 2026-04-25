"""Maintenance commands for KGFS index data."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import connect_runtime, console, optional_config_runtime, runtime
from kgfs.prune import prune_stale_files
from kgfs.reset import rebuild_index, reset_index


def register(app: typer.Typer) -> None:
    app.command("prune")(prune_cmd)
    app.command("reset-index")(reset_index_cmd)
    app.command("rebuild")(rebuild_cmd)


def prune_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report stale database records without removing them."),
) -> None:
    """Remove stale KGFS database records for files that no longer exist."""

    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        summary = prune_stale_files(conn, dry_run=dry_run)
        if dry_run:
            console.print(f"Would prune {len(summary.stale_paths)} stale database records.")
        else:
            console.print(f"Pruned {summary.removed} stale database records.")
        for path in summary.stale_paths[:20]:
            console.print(str(path))
        if len(summary.stale_paths) > 20:
            console.print(f"...and {len(summary.stale_paths) - 20} more")
    finally:
        conn.close()


def reset_index_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show which KGFS database files would be removed."),
    yes: bool = typer.Option(False, "--yes", help="Confirm deletion of KGFS database/index files."),
) -> None:
    """Reset only KGFS database/index files, never source files."""

    _, _, resolved_database_path, _ = optional_config_runtime(config_path, database_path, project_local)
    if not dry_run and not yes:
        if not typer.confirm("Delete KGFS database/index files only?", default=False):
            console.print("Reset cancelled.")
            return
        yes = True
    summary = reset_index(resolved_database_path, dry_run=dry_run, yes=yes)
    if dry_run:
        console.print(f"Would remove KGFS database files for: {resolved_database_path}")
        console.print(f"Existing database files found: {summary.would_remove}")
    else:
        console.print(f"Removed {len(summary.removed_paths)} KGFS database files.")


def rebuild_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    yes: bool = typer.Option(False, "--yes", help="Confirm reset before rebuilding."),
    allow_risky_root: bool = typer.Option(False, "--allow-risky-root", help="Allow indexing risky roots."),
) -> None:
    """Reset the KGFS index database and then run indexing."""

    _, resolved_config_path, resolved_database_path, config = runtime(config_path, database_path, project_local)
    if not config.indexed_folders:
        console.print(f"No indexed folders configured in [bold]{resolved_config_path}[/bold].")
        return
    if not yes and not typer.confirm("Reset KGFS index data and rebuild from configured folders?", default=False):
        console.print("Rebuild cancelled.")
        return
    summary = rebuild_index(config, resolved_database_path, allow_risky_root=allow_risky_root)
    console.print(
        f"Rebuild complete: discovered {summary.discovered}, indexed {summary.indexed}, "
        f"failures {summary.failed}."
    )
