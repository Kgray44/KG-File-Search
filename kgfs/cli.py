"""Typer CLI for KG File Search."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from kgfs.app_dirs import get_app_paths, resolve_config_path, resolve_database_path
from kgfs.config import create_default_config_file, load_config
from kgfs.database import check_fts5_available, connect_database, get_database_stats, initialize_database
from kgfs.file_discovery import discover_files
from kgfs.indexing import index_configured_folders
from kgfs.platform_utils import open_file as open_path
from kgfs.platform_utils import platform_diagnostics, risk_warning
from kgfs.platform_utils import reveal_file as reveal_path
from kgfs.search import get_latest_result_path, hybrid_search, save_latest_results, search, semantic_search
from kgfs.semantic import get_embedder, get_semantic_status

app = typer.Typer(help="KG File Search: private local-first file search.")
console = Console()


def _runtime(
    config_path: Path | None,
    database_path: Path | None,
    project_local: bool,
):
    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    config = load_config(resolved_config_path)
    resolved_database_path = resolve_database_path(app_paths, database_path, config.database_path)
    config = config.model_copy(update={"database_path": resolved_database_path})
    return app_paths, resolved_config_path, resolved_database_path, config


def _connect_runtime(config_path: Path | None, database_path: Path | None, project_local: bool):
    app_paths, resolved_config_path, resolved_database_path, config = _runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    return app_paths, resolved_config_path, resolved_database_path, config, conn


@app.command()
def init(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Store config/data under .kgfs in this project."),
) -> None:
    """Create a config file without indexing anything."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    for directory in (app_paths.config_dir, app_paths.data_dir, app_paths.cache_dir, app_paths.log_dir):
        directory.mkdir(parents=True, exist_ok=True)
    created = create_default_config_file(resolved_config_path)
    console.print(f"Config: [bold]{resolved_config_path}[/bold]")
    console.print(f"Data:   [bold]{app_paths.data_dir}[/bold]")
    console.print(f"Cache:  [bold]{app_paths.cache_dir}[/bold]")
    console.print("Created config file." if created else "Config file already exists; left it unchanged.")
    console.print("Edit indexed_folders, then run: [bold]kgfs index[/bold]")


@app.command()
def doctor(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show environment and configuration diagnostics."""

    app_paths, resolved_config_path, resolved_database_path, config = _runtime(config_path, database_path, project_local)
    diagnostics = platform_diagnostics()
    table = Table(title="KGFS Doctor")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("Platform", diagnostics["platform"])
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Config path", str(resolved_config_path))
    table.add_row("Data path", str(app_paths.data_dir))
    table.add_row("Cache path", str(app_paths.cache_dir))
    table.add_row("Log path", str(app_paths.log_dir))
    table.add_row("Database path", str(resolved_database_path))
    table.add_row("Path separator", diagnostics["path_separator"])
    table.add_row("Home directory", diagnostics["home_directory"])
    table.add_row("Open files", diagnostics["open_files"])
    table.add_row("Reveal files", diagnostics["reveal_files"])
    table.add_row("SQLite FTS5", "available" if check_fts5_available() else "missing")
    table.add_row("Semantic", get_semantic_status(config.semantic).message)
    console.print(table)

    folder_table = Table(title="Configured Folders")
    folder_table.add_column("Folder")
    folder_table.add_column("Exists")
    folder_table.add_column("Readable")
    folder_table.add_column("Warning")
    for folder in config.indexed_folders:
        exists = folder.exists()
        readable = os.access(folder, os.R_OK) if exists else False
        folder_table.add_row(str(folder), str(exists), str(readable), risk_warning(folder))
    console.print(folder_table)


@app.command("config")
def show_config(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Print the active config file."""

    app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
    resolved_config_path = resolve_config_path(app_paths, config_path)
    console.print(f"[bold]Config path:[/bold] {resolved_config_path}")
    console.print(resolved_config_path.read_text(encoding="utf-8"))


@app.command()
def index(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover files without writing to the database."),
    rebuild_embeddings: bool = typer.Option(False, "--rebuild-embeddings", help="Rebuild semantic chunks and embeddings."),
) -> None:
    """Index configured folders."""

    _, _, resolved_database_path, config, conn = _connect_runtime(config_path, database_path, project_local)
    with console.status("Indexing configured folders..."):
        summary = index_configured_folders(
            config,
            conn,
            dry_run=dry_run,
            rebuild_embeddings=rebuild_embeddings,
        )
    console.print(f"Database: [bold]{resolved_database_path}[/bold]")
    console.print(
        f"Discovered {summary.discovered}, indexed {summary.indexed}, "
        f"skipped unchanged {summary.skipped_unchanged}, failures {summary.failed}."
    )
    if dry_run:
        console.print("Dry run only; database was not updated.")


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Natural language or keyword query."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results."),
    hybrid: bool = typer.Option(False, "--hybrid", help="Combine keyword, semantic, filename/path, and recency ranking."),
) -> None:
    """Search indexed files using SQLite FTS5."""

    _, _, _, config, conn = _connect_runtime(config_path, database_path, project_local)
    if hybrid:
        if not config.semantic.enabled:
            raise typer.BadParameter("Hybrid search requires semantic.enabled: true in config.yaml")
        embedder = get_embedder(config.semantic)
        results = hybrid_search(
            conn,
            query,
            embedder=embedder,
            model_name=config.semantic.model_name,
            limit=limit,
        )
    else:
        results = search(conn, query, limit=limit)
    save_latest_results(conn, query, results)
    _print_results(f"Search: {query}", results)


@app.command("semantic")
def semantic_cmd(
    query: str = typer.Argument(..., help="Semantic query."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results."),
) -> None:
    """Search indexed semantic chunks only."""

    _, _, _, config, conn = _connect_runtime(config_path, database_path, project_local)
    if not config.semantic.enabled:
        raise typer.BadParameter("Semantic search requires semantic.enabled: true in config.yaml")
    embedder = get_embedder(config.semantic)
    results = semantic_search(
        conn,
        query,
        embedder=embedder,
        model_name=config.semantic.model_name,
        limit=limit,
    )
    save_latest_results(conn, query, results)
    _print_results(f"Semantic: {query}", results)


def _print_results(title: str, results) -> None:
    table = Table(title=title)
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Score", justify="right")
    table.add_column("Modified")
    table.add_column("Path")
    table.add_column("Snippet")
    for result in results:
        table.add_row(
            str(result.result_id),
            result.file_name,
            result.extension,
            f"{result.score:.3f}",
            _format_timestamp(result.modified_time),
            str(result.path),
            result.snippet,
        )
    console.print(table)
    if not results:
        console.print("No results.")


@app.command()
def open(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Open a file from the latest search results."""

    _, _, _, _, conn = _connect_runtime(config_path, database_path, project_local)
    file_path = get_latest_result_path(conn, result_id)
    if file_path is None:
        raise typer.BadParameter(f"No latest search result with ID {result_id}")
    open_path(file_path)


@app.command()
def reveal(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Reveal a file from the latest search results in the file manager."""

    _, _, _, _, conn = _connect_runtime(config_path, database_path, project_local)
    file_path = get_latest_result_path(conn, result_id)
    if file_path is None:
        raise typer.BadParameter(f"No latest search result with ID {result_id}")
    reveal_path(file_path)


@app.command()
def stats(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show index statistics."""

    _, _, resolved_database_path, _, conn = _connect_runtime(config_path, database_path, project_local)
    stats_data = get_database_stats(conn, resolved_database_path)
    table = Table(title="KGFS Stats")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Total indexed files", str(stats_data["total_files"]))
    table.add_row("Total indexed size", _format_bytes(stats_data["total_size"]))
    table.add_row("Last indexed time", str(stats_data["last_indexed"]))
    table.add_row("Semantic chunks", str(stats_data["total_chunks"]))
    table.add_row("Embedding storage", _format_bytes(stats_data["embedding_bytes"]))
    table.add_row("Extraction failures", str(stats_data["extraction_failures"]))
    table.add_row("Database size", _format_bytes(stats_data["database_size"]))
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
        largest_table.add_row(name, _format_bytes(size), path)
    console.print(largest_table)


@app.command()
def web(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host."),
    port: int = typer.Option(8765, "--port", help="Bind port."),
) -> None:
    """Start the local FastAPI dashboard."""

    import uvicorn

    from kgfs.web.app import create_app

    fastapi_app = create_app(config_path=config_path, database_path=database_path, project_local=project_local)
    console.print(f"Starting KGFS web dashboard at http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port)


def _format_timestamp(value: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


if __name__ == "__main__":
    app()
