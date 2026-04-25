"""Indexing command."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import console, runtime
from kgfs.database import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.prune import prune_stale_files
from kgfs.safety import find_risky_index_roots, format_risky_roots


def register(app: typer.Typer) -> None:
    app.command()(index)


def index(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover files without writing to the database."),
    rebuild_embeddings: bool = typer.Option(False, "--rebuild-embeddings", help="Rebuild semantic chunks and embeddings."),
    force: bool = typer.Option(False, "--force", help="Re-extract and re-index files even if metadata is unchanged."),
    verify_hashes: bool = typer.Option(False, "--verify-hashes", help="Hash-check files even when size and mtime look unchanged."),
    prune: bool = typer.Option(False, "--prune", help="Remove stale KGFS database records after indexing."),
    allow_risky_root: bool = typer.Option(False, "--allow-risky-root", help="Allow indexing risky roots like /, C:\\, or your home folder."),
) -> None:
    """Index configured folders."""

    _, resolved_config_path, resolved_database_path, config = runtime(config_path, database_path, project_local)
    if not config.indexed_folders:
        console.print(
            "No indexed folders configured. Edit indexed_folders in "
            f"[bold]{resolved_config_path}[/bold], then run [bold]kgfs index[/bold]."
        )
        console.print('Example: add "~/Documents/Your Folder" under indexed_folders.')
        return

    risky_roots = find_risky_index_roots(config.indexed_folders)
    if risky_roots and not allow_risky_root:
        console.print("Refusing to index risky root folders:")
        console.print(format_risky_roots(risky_roots))
        console.print("Pass --allow-risky-root only if you intentionally want this broad scan.")
        raise typer.Exit(code=2)

    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        with console.status("Indexing configured folders..."):
            summary = index_configured_folders(
                config,
                conn,
                dry_run=dry_run,
                rebuild_embeddings=rebuild_embeddings,
                allow_risky_root=allow_risky_root,
                force=force,
                verify_hashes=verify_hashes,
            )
        console.print(f"Database: [bold]{resolved_database_path}[/bold]")
        console.print(
            f"Discovered {summary.discovered}, indexed {summary.indexed}, "
            f"skipped unchanged {summary.skipped_unchanged}, failures {summary.failed}."
        )
        if dry_run:
            console.print("Dry run only; database was not updated.")
        elif prune:
            prune_summary = prune_stale_files(conn)
            console.print(f"Pruned {prune_summary.removed} stale database records.")
    finally:
        conn.close()
