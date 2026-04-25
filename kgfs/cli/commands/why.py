"""Explain why a saved search result matched a query."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console
from kgfs.db.latest_results import get_latest_result_record
from kgfs.search.engine import SearchContext
from kgfs.search.explain import explain_result
from kgfs.search.options import SearchOptions
from kgfs.search.registry import SearchModeError, build_default_search_registry
from kgfs.search.result import SearchResult
from kgfs.search.snippets import make_snippet


def register(app: typer.Typer) -> None:
    app.command("why")(why_cmd)


def why_cmd(
    result_id: int = typer.Argument(..., help="Result ID from the latest search results."),
    query: str = typer.Argument(..., help="Query to explain against the latest result."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    mode: str | None = typer.Option(None, "--mode", help="Search mode to use while explaining."),
) -> None:
    """Explain why a latest search result matched a query."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        latest = get_latest_result_record(conn, result_id)
        if latest is None:
            raise typer.BadParameter(f"No latest search result found for ID {result_id}. Run kgfs search first.")

        selected_mode = mode or config.search.default_mode
        try:
            options = SearchOptions(
                mode=selected_mode,
                limit=max(config.search.default_limit, result_id, 25),
                highlight=config.search.highlight_matches,
                save_latest_results=False,
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

        registry = build_default_search_registry()
        context = SearchContext(conn=conn, config=config)
        notes: list[str] = []
        try:
            execution = registry.search(query, options, context)
        except SearchModeError as exc:
            raise typer.BadParameter(str(exc)) from exc

        result = _find_matching_result(execution.results, latest.file_id, latest.file_path)
        if result is None:
            result = _load_latest_file_as_result(conn, latest.file_id, result_id, query, config.search.highlight_matches)
            notes.append("The result did not appear in a fresh search rerun; showing the saved file with best available local context.")
        else:
            result = _with_result_id(result, result_id)

        explanation = explain_result(result, query, mode_used=execution.mode_used, notes=notes)
        for warning in execution.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        _print_explanation(explanation)
    finally:
        conn.close()


def _find_matching_result(results: list[SearchResult], file_id: int, path: Path) -> SearchResult | None:
    for result in results:
        if result.file_id == file_id:
            return result
    path_text = str(path)
    for result in results:
        if str(result.path) == path_text:
            return result
    return None


def _load_latest_file_as_result(conn, file_id: int, result_id: int, query: str, highlight: bool) -> SearchResult:
    row = conn.execute(
        """
        SELECT id, file_name, path, normalized_path, extension, modified_time, extracted_text, extraction_source
        FROM files
        WHERE id = ?
        """,
        (file_id,),
    ).fetchone()
    if row is None:
        raise typer.BadParameter(
            f"Latest result ID {result_id} points to a file record that is no longer in the KGFS index."
        )
    snippet = make_snippet(row["extracted_text"], query, highlight=highlight)
    return SearchResult(
        result_id=result_id,
        file_id=int(row["id"]),
        file_name=row["file_name"],
        path=Path(row["path"]),
        extension=row["extension"],
        modified_time=float(row["modified_time"]),
        score=0.0,
        snippet=snippet,
        normalized_path=row["normalized_path"],
        score_breakdown={"final": 0.0},
        mode="keyword",
        source="latest",
        metadata={"extraction_source": row["extraction_source"]},
    )


def _with_result_id(result: SearchResult, result_id: int) -> SearchResult:
    return SearchResult(
        result_id=result_id,
        file_id=result.file_id,
        file_name=result.file_name,
        path=result.path,
        extension=result.extension,
        modified_time=result.modified_time,
        score=result.score,
        snippet=result.snippet,
        normalized_path=result.normalized_path,
        score_breakdown=result.score_breakdown,
        matched_chunk_id=result.matched_chunk_id,
        mode=result.mode,
        source=result.source,
        metadata=result.metadata,
    )


def _print_explanation(explanation) -> None:
    console.print(f"[bold]Why result {explanation.result_id} matched[/bold]")
    console.print(f"File: {explanation.file_name}")
    console.print(f"Path: {explanation.path}")
    console.print(f"Mode: {explanation.mode.value}")
    if explanation.final_score is not None:
        console.print(f"Final score: {explanation.final_score:.3f}")
    console.print(explanation.summary)

    table = Table(title="Score breakdown")
    table.add_column("Component")
    table.add_column("Value", justify="right")
    for key, value in (explanation.score_breakdown or {}).items():
        table.add_row(key, f"{value:.3f}")
    console.print(table)

    if explanation.snippet:
        console.print("[bold]Matched snippet[/bold]")
        console.print(explanation.snippet)
    for note in explanation.notes:
        console.print(f"[yellow]Note:[/yellow] {note}")
