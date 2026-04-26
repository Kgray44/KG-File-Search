"""FastAPI application factory for the local-only KGFS JSON API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from kgfs.api.auth import APIAuthSettings
from kgfs.api.routes import build_router
from kgfs.core.app_dirs import get_app_paths, resolve_config_path, resolve_database_path
from kgfs.core.config import load_config
from kgfs.db import connect_database, initialize_database


def create_api_app(
    *,
    config_path: Path | None = None,
    database_path: Path | None = None,
    project_local: bool = False,
) -> FastAPI:
    app = FastAPI(title="KGFS Local API")

    def runtime():
        app_paths = get_app_paths(project_local=project_local, project_root=Path.cwd())
        resolved_config_path = resolve_config_path(app_paths, config_path)
        config = load_config(resolved_config_path)
        resolved_database_path = resolve_database_path(app_paths, database_path, config.database_path)
        config = config.model_copy(update={"database_path": resolved_database_path})
        conn = connect_database(resolved_database_path)
        initialize_database(conn)
        return resolved_config_path, resolved_database_path, config, conn

    _, _, config, conn = runtime()
    conn.close()
    app.include_router(build_router(runtime, APIAuthSettings(config.api.require_token, config.api.token_env)))
    return app
