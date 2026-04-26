"""Local-only KGFS JSON API command."""

from __future__ import annotations

from pathlib import Path

import typer

from kgfs.api.auth import token_from_env, validate_api_bind
from kgfs.cli.shared import console, runtime


def register(app: typer.Typer) -> None:
    app.command("serve")(serve_cmd)


def serve_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    host: str | None = typer.Option(None, "--host", help="Bind host. Defaults to api.host."),
    port: int | None = typer.Option(None, "--port", help="Bind port. Defaults to api.port."),
    local_only: bool = typer.Option(True, "--local-only/--no-local-only", help="Refuse non-localhost binds."),
    allow_network: bool = typer.Option(False, "--allow-network", help="Explicitly allow non-localhost bind."),
    no_token: bool = typer.Option(False, "--no-token", help="Disable API token requirement for this run."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate settings without starting the server."),
) -> None:
    """Start the local-only KGFS JSON API."""

    _, _, _, config = runtime(config_path, database_path, project_local)
    bind_host = host or config.api.host
    bind_port = port or config.api.port
    try:
        validate_api_bind(bind_host, allow_network=allow_network)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if local_only and not allow_network and bind_host not in {"127.0.0.1", "localhost", "::1"}:
        raise typer.BadParameter("Use --allow-network and --no-local-only to bind KGFS API outside 127.0.0.1.")

    require_token = config.api.require_token and not no_token
    if require_token and not token_from_env(config.api.token_env):
        raise typer.BadParameter(f"Set {config.api.token_env} or pass --no-token for localhost-only development.")
    if dry_run:
        console.print(f"Dry run: KGFS API would listen on http://{bind_host}:{bind_port}")
        console.print(f"Token required: {require_token}")
        console.print(f"File actions enabled: {config.api.allow_file_actions}")
        return

    import uvicorn

    from kgfs.api.app import create_api_app

    console.print(f"Starting KGFS local API at http://{bind_host}:{bind_port}")
    api_app = create_api_app(config_path=config_path, database_path=database_path, project_local=project_local)
    uvicorn.run(api_app, host=bind_host, port=bind_port)
