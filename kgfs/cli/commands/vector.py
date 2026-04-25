"""Vector index management commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console
from kgfs.search.backends import UnknownVectorBackend, get_vector_backend
from kgfs.search.engine import SearchContext
from kgfs.vectors.index_manager import rebuild_vector_index
from kgfs.vectors.status import get_vector_status


vector_app = typer.Typer(help="Manage local semantic vector data.")


def register(app: typer.Typer) -> None:
    app.add_typer(vector_app, name="vector")


@vector_app.command("status")
def vector_status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show semantic vector index status."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        status = get_vector_status(conn, config)
    finally:
        conn.close()

    table = Table(title="KGFS Vector Status")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("Semantic enabled", str(status.semantic_enabled))
    table.add_row("Model", status.model_name)
    table.add_row("Backend", status.backend_name)
    table.add_row("Backend available", str(status.backend_available))
    table.add_row("Semantic dependencies", str(status.semantic_dependencies_available))
    table.add_row("Chunks", str(status.chunk_count))
    table.add_row("Files with chunks", str(status.file_count_with_chunks))
    table.add_row("Ready", str(status.chunks_ready and status.backend_available))
    console.print(table)
    for warning in status.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


@vector_app.command("rebuild")
def vector_rebuild_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    force: bool = typer.Option(True, "--force/--no-force", help="Rebuild chunks even when chunks already exist."),
) -> None:
    """Rebuild semantic chunks from already indexed extracted text."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        if not config.semantic.enabled:
            raise typer.BadParameter("Semantic search is disabled. Set semantic.enabled: true before rebuilding vectors.")
        try:
            get_vector_backend(config.vectors.backend)
        except UnknownVectorBackend as exc:
            raise typer.BadParameter(str(exc)) from exc
        with console.status("Rebuilding local vector index..."):
            summary = rebuild_vector_index(config, conn, force=force)
        console.print(
            f"Vector rebuild complete: files considered {summary.files_considered}, "
            f"files indexed {summary.files_indexed}, chunks indexed {summary.chunks_indexed}, "
            f"skipped without text {summary.skipped_no_text}."
        )
    finally:
        conn.close()


@vector_app.command("clear")
def vector_clear_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    yes: bool = typer.Option(False, "--yes", help="Confirm clearing KGFS vector/chunk data only."),
) -> None:
    """Clear KGFS vector/chunk data only."""

    if not yes:
        raise typer.BadParameter("Pass --yes to clear KGFS vector/chunk data.")
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            backend = get_vector_backend(config.vectors.backend)
        except UnknownVectorBackend as exc:
            raise typer.BadParameter(str(exc)) from exc
        removed = backend.clear(SearchContext(conn=conn, config=config), model_name=config.semantic.model_name)
        console.print(f"Removed {removed} vector chunks for model {config.semantic.model_name}.")
        console.print("Source files, file records, and keyword FTS rows were left unchanged.")
    finally:
        conn.close()
