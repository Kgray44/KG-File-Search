"""FastAPI dashboard for KGFS."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from kgfs.core.app_dirs import get_app_paths, resolve_config_path, resolve_database_path
from kgfs.core.config import load_config
from kgfs.core.platform_utils import open_file, reveal_file
from kgfs.core.resources import web_static_dir, web_templates_dir
from kgfs.db import connect_database, get_database_stats, initialize_database
from kgfs.db.latest_results import get_latest_result_path, save_latest_results
from kgfs.intelligence.graph import build_topic_graph
from kgfs.intelligence.health import build_health_report
from kgfs.media.status import get_media_status
from kgfs.ocr.status import get_ocr_status
from kgfs.search import SearchContext, SearchFilters, SearchModeError, SearchOptions, build_default_search_registry
from kgfs.vectors.status import get_vector_status
from kgfs.workflows.collections import list_collections
from kgfs.workflows.notes import notes_for_file
from kgfs.workflows.projects import list_projects
from kgfs.workflows.tags import list_all_tags

templates = Jinja2Templates(directory=str(web_templates_dir()))


def create_app(
    *,
    config_path: Path | None = None,
    database_path: Path | None = None,
    project_local: bool = False,
) -> FastAPI:
    app = FastAPI(title="KG File Search")
    app.mount("/static", StaticFiles(directory=str(web_static_dir())), name="static")

    def runtime():
        app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
        resolved_config_path = resolve_config_path(app_paths, config_path)
        config = load_config(resolved_config_path)
        resolved_database_path = resolve_database_path(app_paths, database_path, config.database_path)
        conn = connect_database(resolved_database_path)
        initialize_database(conn)
        return resolved_config_path, resolved_database_path, config, conn

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        _, database, config, conn = runtime()
        try:
            stats = get_database_stats(conn, database)
            vector_status = get_vector_status(conn, config)
            ocr_status = get_ocr_status(config, conn)
            media_status = get_media_status(config, conn)
            health = build_health_report(conn, config, database_path=database)
            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "stats": stats,
                    "vector_status": vector_status,
                    "ocr_status": ocr_status,
                    "media_status": media_status,
                    "health": health,
                },
            )
        finally:
            conn.close()

    @app.get("/search", response_class=HTMLResponse)
    def search_page(
        request: Request,
        q: str = "",
        ext: str = "",
        folder: str = "",
        after: str = "",
        before: str = "",
        limit: int = 10,
        failed_only: bool = False,
        mode: str = "auto",
    ):
        _, _, config, conn = runtime()
        try:
            filters = SearchFilters(
                extensions=[ext] if ext else None,
                folder=folder or None,
                after=after or None,
                before=before or None,
                failed_only=failed_only,
            )
            results = []
            mode_used = mode
            warnings: list[str] = []
            error = ""
            if q:
                try:
                    options = SearchOptions(
                        mode=mode,
                        limit=max(1, min(limit, 100)),
                        filters=filters,
                        highlight=config.search.highlight_matches,
                    )
                    execution = build_default_search_registry().search(q, options, SearchContext(conn=conn, config=config))
                    results = execution.results
                    mode_used = execution.mode_used.value
                    warnings = execution.warnings
                    save_latest_results(conn, q, results)
                except (SearchModeError, ValueError) as exc:
                    error = str(exc)
            result_metadata = _result_metadata(conn, [result.file_id for result in results])
            return templates.TemplateResponse(
                request,
                "search.html",
                {
                    "query": q,
                    "results": results,
                    "filters": {
                        "ext": ext,
                        "folder": folder,
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "failed_only": failed_only,
                        "mode": mode,
                    },
                    "mode_used": mode_used,
                    "warnings": warnings,
                    "error": error,
                    "result_metadata": result_metadata,
                    "modes": ["auto", "keyword", "semantic", "hybrid"],
                },
            )
        finally:
            conn.close()

    @app.get("/stats", response_class=HTMLResponse)
    def stats_page(request: Request):
        _, database, _, conn = runtime()
        try:
            stats = get_database_stats(conn, database)
            return templates.TemplateResponse(request, "stats.html", {"stats": stats})
        finally:
            conn.close()

    @app.get("/config", response_class=HTMLResponse)
    def config_page(request: Request):
        resolved_config_path, _, config, conn = runtime()
        try:
            return templates.TemplateResponse(
                request,
                "config.html",
                {
                    "config_path": resolved_config_path,
                    "config": config.model_dump(),
                    "folders": config.indexed_folders,
                },
            )
        finally:
            conn.close()

    @app.get("/failures", response_class=HTMLResponse)
    def failures_page(request: Request):
        _, _, _, conn = runtime()
        try:
            rows = conn.execute(
                """
                SELECT file_name, path, extraction_error
                FROM files
                WHERE extraction_status = 'error'
                ORDER BY indexed_at DESC
                LIMIT 100
                """
            ).fetchall()
            failures = [
                {
                    "file_name": row["file_name"],
                    "path": row["path"],
                    "extraction_error": row["extraction_error"],
                }
                for row in rows
            ]
            return templates.TemplateResponse(request, "failures.html", {"failures": failures})
        finally:
            conn.close()

    @app.get("/collections", response_class=HTMLResponse)
    def collections_page(request: Request):
        _, _, _, conn = runtime()
        try:
            return templates.TemplateResponse(request, "collections.html", {"collections": list_collections(conn)})
        finally:
            conn.close()

    @app.get("/tags", response_class=HTMLResponse)
    def tags_page(request: Request):
        _, _, _, conn = runtime()
        try:
            return templates.TemplateResponse(request, "tags.html", {"tags": list_all_tags(conn)})
        finally:
            conn.close()

    @app.get("/projects", response_class=HTMLResponse)
    def projects_page(request: Request):
        _, _, _, conn = runtime()
        try:
            return templates.TemplateResponse(request, "projects.html", {"projects": list_projects(conn)})
        finally:
            conn.close()

    @app.get("/health", response_class=HTMLResponse)
    def health_page(request: Request):
        _, database, config, conn = runtime()
        try:
            health = build_health_report(conn, config, database_path=database)
            return templates.TemplateResponse(request, "health.html", {"health": health})
        finally:
            conn.close()

    @app.get("/graph", response_class=HTMLResponse)
    def graph_page(request: Request, q: str = ""):
        _, _, config, conn = runtime()
        try:
            graph = build_topic_graph(conn, q, config) if q else None
            return templates.TemplateResponse(request, "graph.html", {"query": q, "graph": graph})
        finally:
            conn.close()

    @app.get("/open/{result_id}", response_class=PlainTextResponse)
    def open_result(result_id: int):
        _, _, _, conn = runtime()
        try:
            file_path = get_latest_result_path(conn, result_id)
        finally:
            conn.close()
        if file_path is None:
            return PlainTextResponse("No latest search result with that ID.", status_code=404)
        open_file(file_path)
        return PlainTextResponse(f"Opened {file_path}")

    @app.get("/reveal/{result_id}", response_class=PlainTextResponse)
    def reveal_result(result_id: int):
        _, _, _, conn = runtime()
        try:
            file_path = get_latest_result_path(conn, result_id)
        finally:
            conn.close()
        if file_path is None:
            return PlainTextResponse("No latest search result with that ID.", status_code=404)
        reveal_file(file_path)
        return PlainTextResponse(f"Revealed {file_path}")

    return app


def _result_metadata(conn, file_ids: list[int]) -> dict[int, dict[str, object]]:
    metadata: dict[int, dict[str, object]] = {}
    for file_id in file_ids:
        tags = [
            row["name"]
            for row in conn.execute(
                """
                SELECT t.name
                FROM file_tags ft
                JOIN tags t ON t.id = ft.tag_id
                WHERE ft.file_id = ?
                ORDER BY t.name
                """,
                (file_id,),
            ).fetchall()
        ]
        metadata[file_id] = {
            "tags": tags,
            "notes": notes_for_file(conn, file_id)[:3],
        }
    return metadata
