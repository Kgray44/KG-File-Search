"""Semantic search commands."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import connect_runtime, console, format_bytes, print_results
from kgfs.db import get_database_stats
from kgfs.search import save_latest_results, semantic_search
from kgfs.search.semantic import get_embedder, get_semantic_status
from kgfs.vectors.index_manager import rebuild_vector_index
from kgfs.vectors.status import get_vector_status


def register(app: typer.Typer) -> None:
    app.command("semantic")(semantic_cmd)
    app.command("semantic-index")(semantic_index_cmd)


def semantic_cmd(
    query: str = typer.Argument(..., help="Semantic query."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results."),
) -> None:
    """Search indexed semantic chunks only."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        if not config.semantic.enabled:
            raise typer.BadParameter("Semantic search requires semantic.enabled: true in config.yaml")
        embedder = get_embedder(config.semantic)
        results = semantic_search(
            conn,
            query,
            embedder=embedder,
            model_name=config.semantic.model_name,
            backend_name=config.vectors.backend,
            limit=limit,
            highlight=True,
        )
        save_latest_results(conn, query, results)
        print_results(f"Semantic: {query}", results)
    finally:
        conn.close()


def semantic_index_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    rebuild: bool = typer.Option(False, "--rebuild", help="Build or rebuild semantic chunks and embeddings."),
    allow_risky_root: bool = typer.Option(False, "--allow-risky-root", help="Allow indexing risky roots during rebuild."),
) -> None:
    """Show semantic index status, optionally rebuilding local embeddings."""

    _, _, resolved_database_path, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        status = get_semantic_status(config.semantic)
        vector_status = get_vector_status(conn, config)
        stats_data = get_database_stats(conn, resolved_database_path)
        console.print(f"Semantic: {status.message}")
        console.print(f"Model: {config.semantic.model_name}")
        console.print(f"Backend: {vector_status.backend_name}")
        console.print(f"Chunks: {vector_status.chunk_count}")
        console.print(f"Embedding storage: {format_bytes(stats_data['embedding_bytes'])}")
        if rebuild:
            if not config.semantic.enabled:
                raise typer.BadParameter("Semantic indexing requires semantic.enabled: true in config.yaml")
            with console.status("Rebuilding semantic chunks..."):
                summary = rebuild_vector_index(config, conn, force=True)
            console.print(
                f"Semantic rebuild pass complete: files considered {summary.files_considered}, "
                f"files indexed {summary.files_indexed}, chunks indexed {summary.chunks_indexed}."
            )
    finally:
        conn.close()
