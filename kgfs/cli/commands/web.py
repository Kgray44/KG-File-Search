"""Web dashboard command."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.cli.shared import console


def register(app: typer.Typer) -> None:
    app.command()(web)


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
