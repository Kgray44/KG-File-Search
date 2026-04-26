"""Search profile commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console, print_results
from kgfs.workflows.profiles import create_profile, delete_profile, get_profile, list_profiles, profile_search


profile_app = typer.Typer(help="Manage local search profiles.")


def register(app: typer.Typer) -> None:
    app.add_typer(profile_app, name="profile")


@profile_app.command("list")
def profile_list_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title="Profiles")
        table.add_column("Name")
        table.add_column("Mode")
        table.add_column("Extensions")
        table.add_column("Folders")
        for profile in list_profiles(conn):
            table.add_row(profile.name, profile.default_mode, ", ".join(profile.extensions), ", ".join(profile.folders))
        console.print(table)
    finally:
        conn.close()


@profile_app.command("create")
def profile_create_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    folder: list[Path] | None = typer.Option(None, "--folder", help="Folder/path substring constraint."),
    ext: list[str] | None = typer.Option(None, "--ext", help="Extension constraint."),
    mode: str = typer.Option("auto", "--mode", help="Default search mode."),
    boost_term: list[str] | None = typer.Option(None, "--boost-term", help="Local query boost term."),
    description: str | None = typer.Option(None, "--description", help="Profile description."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        profile = create_profile(
            conn,
            name,
            folders=folder,
            extensions=ext,
            default_mode=mode,
            boost_terms=boost_term,
            description=description,
        )
        console.print(f"Created profile: {profile.name}")
    finally:
        conn.close()


@profile_app.command("show")
def profile_show_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        profile = get_profile(conn, name)
        if profile is None:
            raise typer.BadParameter(f"Unknown profile: {name}")
        console.print(profile)
    finally:
        conn.close()


@profile_app.command("delete")
def profile_delete_cmd(
    name: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Deleted profile." if delete_profile(conn, name) else "Profile not found.")
    finally:
        conn.close()


@profile_app.command("search")
def profile_search_cmd(
    name: str,
    query: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum results."),
    mode: str | None = typer.Option(None, "--mode", help="Override profile mode."),
) -> None:
    _, _, _, config, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            report = profile_search(conn, name, query, config, limit=limit, mode=mode)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        for warning in report.warnings:
            console.print(f"[yellow]Warning:[/yellow] {warning}")
        print_results(f"Profile {name}: {query}", report.results)
    finally:
        conn.close()
