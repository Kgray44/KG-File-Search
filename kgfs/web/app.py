"""FastAPI dashboard for KGFS."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from kgfs.app_dirs import get_app_paths, resolve_config_path, resolve_database_path
from kgfs.config import load_config
from kgfs.database import connect_database, get_database_stats, initialize_database
from kgfs.search import save_latest_results, search

WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def create_app(
    *,
    config_path: Path | None = None,
    database_path: Path | None = None,
    project_local: bool = False,
) -> FastAPI:
    app = FastAPI(title="KG File Search")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

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
        stats = get_database_stats(conn, database)
        return templates.TemplateResponse("index.html", {"request": request, "stats": stats})

    @app.get("/search", response_class=HTMLResponse)
    def search_page(request: Request, q: str = ""):
        _, _, _, conn = runtime()
        results = search(conn, q) if q else []
        if q:
            save_latest_results(conn, q, results)
        return templates.TemplateResponse("search.html", {"request": request, "query": q, "results": results})

    @app.get("/stats", response_class=HTMLResponse)
    def stats_page(request: Request):
        _, database, _, conn = runtime()
        stats = get_database_stats(conn, database)
        return templates.TemplateResponse("stats.html", {"request": request, "stats": stats})

    @app.get("/config", response_class=HTMLResponse)
    def config_page(request: Request):
        resolved_config_path, _, config, _ = runtime()
        return templates.TemplateResponse(
            "config.html",
            {"request": request, "config_path": resolved_config_path, "config": config.model_dump()},
        )

    return app

