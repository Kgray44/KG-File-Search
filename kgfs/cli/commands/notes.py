"""Note commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import connect_runtime, console
from kgfs.workflows.notes import add_note, delete_note, list_notes


def register(app: typer.Typer) -> None:
    app.command("note", help="Attach a local note to a latest result.")(note_cmd)
    app.command("notes", help="List local notes for a latest result.")(notes_cmd)
    app.command("note-delete", help="Delete a local note by note ID.")(note_delete_cmd)


def note_cmd(
    result_id: int,
    note_text: str,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        try:
            note = add_note(conn, result_id, note_text)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.print(f"Added note {note.id}.")
    finally:
        conn.close()


def notes_cmd(
    result_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        table = Table(title=f"Notes for result {result_id}")
        table.add_column("ID")
        table.add_column("Note")
        for note in list_notes(conn, result_id):
            table.add_row(str(note.id), note.note)
        console.print(table)
    finally:
        conn.close()


def note_delete_cmd(
    note_id: int,
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, _, conn = connect_runtime(config_path, database_path, project_local)
    try:
        console.print("Deleted note." if delete_note(conn, note_id) else "Note not found.")
    finally:
        conn.close()
