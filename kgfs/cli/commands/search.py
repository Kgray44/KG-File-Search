"""Search and AI Assist commands."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.ai import AIError, answer_question_with_ai, build_ai_context, get_openai_client, rerank_results_with_ai
from kgfs.cli.shared import (
    connect_runtime,
    console,
    ensure_ai_ready,
    preview_or_confirm_ai_context,
    print_results,
    runtime,
)
from kgfs.db import connect_database, initialize_database
from kgfs.search import SearchFilters, hybrid_search, save_latest_results, search
from kgfs.search.semantic import get_embedder


def register(app: typer.Typer) -> None:
    app.command("search")(search_cmd)
    app.command("ask")(ask_cmd)


def search_cmd(
    query: str = typer.Argument(..., help="Natural language or keyword query."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum results."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Filter by extension, e.g. --ext .pdf."),
    file_type: str | None = typer.Option(None, "--type", help="Filter by file type/extension, e.g. --type pdf."),
    folder: str | None = typer.Option(None, "--folder", help="Filter by folder/path substring."),
    after: str | None = typer.Option(None, "--after", help="Only files modified on/after YYYY-MM-DD."),
    before: str | None = typer.Option(None, "--before", help="Only files modified on/before YYYY-MM-DD."),
    failed_only: bool = typer.Option(False, "--failed-only", help="Show only extraction failures."),
    hybrid: bool = typer.Option(False, "--hybrid", help="Combine keyword, semantic, filename/path, and recency ranking."),
    ai_rerank: bool = typer.Option(False, "--ai-rerank", help="Use opt-in OpenAI AI Assist to rerank local results."),
    preview_ai_context: bool = typer.Option(False, "--preview-ai-context", help="Print AI context and do not send it."),
) -> None:
    """Search indexed files using SQLite FTS5."""

    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    filters = SearchFilters(
        extensions=ext,
        file_type=file_type,
        folder=folder,
        after=after,
        before=before,
        failed_only=failed_only,
    )
    try:
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
                filters=filters,
                highlight=True,
            )
        else:
            results = search(conn, query, limit=limit, filters=filters, highlight=True)

        if ai_rerank:
            try:
                ensure_ai_ready(config, feature="rerank")
                context = build_ai_context(query, results, config.ai)
                if preview_or_confirm_ai_context(context, config.ai, preview_ai_context):
                    client = get_openai_client(config.ai)
                    results = rerank_results_with_ai(query, results, config.ai, client)
            except AIError as exc:
                raise typer.BadParameter(str(exc)) from exc

        save_latest_results(conn, query, results)
        print_results(f"Search: {query}", results)
    finally:
        conn.close()


def ask_cmd(
    question: str = typer.Argument(..., help="Question to answer from local search results."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum local results to include."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Filter local search by extension."),
    folder: str | None = typer.Option(None, "--folder", help="Filter local search by folder/path substring."),
    after: str | None = typer.Option(None, "--after", help="Only files modified on/after YYYY-MM-DD."),
    before: str | None = typer.Option(None, "--before", help="Only files modified on/before YYYY-MM-DD."),
    preview_ai_context: bool = typer.Option(False, "--preview-ai-context", help="Print AI context and do not send it."),
) -> None:
    """Ask OpenAI a question using only local KGFS search snippets."""

    try:
        _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
        ensure_ai_ready(config, feature="answer")
        conn = connect_database(resolved_database_path)
        try:
            initialize_database(conn)
            filters = SearchFilters(extensions=ext, folder=folder, after=after, before=before)
            results = search(conn, question, limit=limit or config.ai.max_results_sent, filters=filters)
            save_latest_results(conn, question, results)
        finally:
            conn.close()
        context = build_ai_context(question, results, config.ai)
        if not preview_or_confirm_ai_context(context, config.ai, preview_ai_context):
            return
        client = get_openai_client(config.ai)
        answer = answer_question_with_ai(question, results, config.ai, client)
    except AIError as exc:
        raise typer.BadParameter(str(exc)) from exc

    console.print("[bold]AI Assist Answer[/bold]")
    console.print(answer.text)
