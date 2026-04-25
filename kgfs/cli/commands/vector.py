"""Vector index management commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console
from kgfs.search.backends import UnknownVectorBackend, backend_availability_by_name, get_vector_backend, list_vector_backend_names
from kgfs.search.engine import SearchContext
from kgfs.search.semantic import SemanticUnavailableError, get_embedder
from kgfs.vectors.benchmark import benchmark_vector_backends
from kgfs.vectors.index_manager import rebuild_vector_index
from kgfs.vectors.recommend import recommend_vector_backend
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
        availability_by_name = backend_availability_by_name(SearchContext(conn=conn, config=config))
    finally:
        conn.close()

    table = Table(title="KGFS Vector Status")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("Semantic enabled", str(status.semantic_enabled))
    table.add_row("Model", status.model_name)
    table.add_row("Backend", status.backend_name)
    table.add_row("Known backends", ", ".join(status.metadata.get("known_backends", [])))
    table.add_row("Backend available", str(status.backend_available))
    table.add_row("Artifact status", str(status.metadata.get("artifact_status", "n/a")))
    if status.artifact_path:
        table.add_row("Artifact path", str(status.artifact_path))
    table.add_row("Semantic dependencies", str(status.semantic_dependencies_available))
    table.add_row("Chunks", str(status.chunk_count))
    table.add_row("Files with chunks", str(status.file_count_with_chunks))
    table.add_row("Ready", str(status.chunks_ready and status.backend_available))
    console.print(table)
    backend_table = Table(title="Known Vector Backends")
    backend_table.add_column("Backend", no_wrap=True)
    backend_table.add_column("Available")
    backend_table.add_column("Message")
    for name, availability in availability_by_name.items():
        backend_table.add_row(name, "yes" if availability.available else "no", availability.message)
    console.print(backend_table)
    for warning in status.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


@vector_app.command("rebuild")
def vector_rebuild_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    force: bool = typer.Option(True, "--force/--no-force", help="Rebuild chunks even when chunks already exist."),
    backend_name: str | None = typer.Option(None, "--backend", help="Backend to rebuild. Defaults to vectors.backend."),
) -> None:
    """Rebuild semantic chunks from already indexed extracted text."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        if not config.semantic.enabled:
            raise typer.BadParameter("Semantic search is disabled. Set semantic.enabled: true before rebuilding vectors.")
        selected_backend = backend_name or config.vectors.backend
        try:
            backend = get_vector_backend(selected_backend)
        except UnknownVectorBackend as exc:
            raise typer.BadParameter(str(exc)) from exc
        if backend.name == "sqlite_scan":
            with console.status("Rebuilding local vector chunks..."):
                summary = rebuild_vector_index(config, conn, force=force)
            console.print(
                f"Vector rebuild complete: files considered {summary.files_considered}, "
                f"files indexed {summary.files_indexed}, chunks indexed {summary.chunks_indexed}, "
                f"skipped without text {summary.skipped_no_text}."
            )
            console.print("sqlite_scan uses SQLite chunks directly; no backend artifact was created.")
            return
        try:
            with console.status(f"Rebuilding {backend.name} vector backend artifact..."):
                summary = backend.rebuild(SearchContext(conn=conn, config=config), model_name=config.semantic.model_name)
        except RuntimeError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(summary.message or f"{backend.name} backend rebuild complete.")
        console.print(f"Chunks indexed in backend artifact: {summary.chunk_count}.")
        if summary.artifact_path:
            console.print(f"Artifact: {summary.artifact_path}")
    finally:
        conn.close()


@vector_app.command("clear")
def vector_clear_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    yes: bool = typer.Option(False, "--yes", help="Confirm clearing KGFS vector/chunk data only."),
    backend_name: str | None = typer.Option(None, "--backend", help="Clear artifacts for one backend. Defaults to chunks."),
    all_backends: bool = typer.Option(False, "--all-backends", help="Clear backend artifacts for all optional backends."),
) -> None:
    """Clear KGFS vector/chunk data only."""

    if not yes:
        raise typer.BadParameter("Pass --yes to clear KGFS vector/chunk data.")
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        if all_backends:
            removed = 0
            for name in list_vector_backend_names():
                if name == "sqlite_scan":
                    continue
                removed += get_vector_backend(name).clear(SearchContext(conn=conn, config=config), model_name=config.semantic.model_name)
            console.print(f"Removed {removed} backend artifact entries for optional vector backends.")
            console.print("Source files, file records, chunks, and keyword FTS rows were left unchanged.")
            return

        selected_backend = backend_name or config.vectors.backend
        try:
            backend = get_vector_backend(selected_backend)
        except UnknownVectorBackend as exc:
            raise typer.BadParameter(str(exc)) from exc
        removed = backend.clear(SearchContext(conn=conn, config=config), model_name=config.semantic.model_name)
        if backend.name == "sqlite_scan" and backend_name is None:
            console.print(f"Removed {removed} vector chunks for model {config.semantic.model_name}.")
        elif backend.name == "sqlite_scan":
            console.print(f"Removed {removed} vector chunks for model {config.semantic.model_name}.")
        else:
            console.print(f"Removed {removed} backend artifact entries for {backend.name}.")
        console.print("Source files, file records, and keyword FTS rows were left unchanged.")
    finally:
        conn.close()


@vector_app.command("benchmark")
def vector_benchmark_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    backend_names: list[str] | None = typer.Option(None, "--backend", help="Benchmark one backend. Can be repeated."),
    queries: list[str] | None = typer.Option(None, "--query", "--queries", help="Query text to embed for benchmarking."),
    limit: int = typer.Option(10, "--limit", help="Vector hit limit per benchmark query."),
) -> None:
    """Benchmark available vector backends against local vector data."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        embedder = None
        if queries:
            try:
                embedder = get_embedder(config.semantic)
            except SemanticUnavailableError as exc:
                raise typer.BadParameter(str(exc)) from exc
        results = benchmark_vector_backends(
            conn,
            config,
            backend_names=backend_names,
            query_texts=queries,
            embedder=embedder,
            limit=limit,
        )
    finally:
        conn.close()

    table = Table(title="KGFS Vector Benchmark")
    table.add_column("Backend", no_wrap=True)
    table.add_column("Avail", no_wrap=True)
    table.add_column("Chunks", justify="right")
    table.add_column("Artifact")
    table.add_column("Queries", justify="right")
    table.add_column("Avg Time", justify="right", no_wrap=True)
    table.add_column("Notes")
    for item in results:
        avg = "n/a" if item.average_query_seconds is None else f"{item.average_query_seconds:.4f}s"
        table.add_row(
            item.backend_name,
            "yes" if item.available else "no",
            str(item.chunk_count),
            item.artifact_status,
            str(item.query_count),
            avg,
            "; ".join(item.notes),
        )
    console.print(table)


@vector_app.command("recommend")
def vector_recommend_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Recommend a vector backend for the current local index."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        recommendation = recommend_vector_backend(conn, config)
    finally:
        conn.close()

    console.print(f"[bold]Recommended backend:[/bold] {recommendation.backend_name}")
    for reason in recommendation.reasons:
        console.print(f"- {reason}")
    for warning in recommendation.warnings:
        if warning:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
