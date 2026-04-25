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
from kgfs.search import SearchFilters, search

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
        _, database, _, conn = runtime()
        try:
            stats = get_database_stats(conn, database)
            return templates.TemplateResponse(request, "index.html", {"stats": stats})
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
    ):
        _, _, _, conn = runtime()
        try:
            filters = SearchFilters(
                extensions=[ext] if ext else None,
                folder=folder or None,
                after=after or None,
                before=before or None,
                failed_only=failed_only,
            )
            results = search(conn, q, limit=limit, filters=filters) if q else []
            if q:
                save_latest_results(conn, q, results)
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
                    },
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
