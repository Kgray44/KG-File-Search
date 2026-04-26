"""Media and multimodal scaffold commands."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer
from rich.table import Table

from kgfs.cli.shared import console, format_bytes, optional_config_runtime, runtime
from kgfs.db import connect_database, initialize_database
from kgfs.indexing import index_configured_folders
from kgfs.media.audio import get_audio_status, index_existing_transcripts, transcribe_audio
from kgfs.media.cache import clear_media_data
from kgfs.media.captions import caption_image, get_caption_status, index_existing_captions
from kgfs.media.exif import extract_exif_metadata, photo_metadata_text
from kgfs.media.metadata import index_existing_photo_metadata
from kgfs.media.status import get_media_status
from kgfs.media.visual import find_visual_similar, get_visual_status, index_existing_visual_embeddings

media_app = typer.Typer(help="Inspect and manage optional local media metadata.")
captions_app = typer.Typer(help="Image caption scaffold commands.")
audio_app = typer.Typer(help="Audio transcription scaffold commands.")
visual_app = typer.Typer(help="Visual search scaffold commands.")


def register(app: typer.Typer) -> None:
    media_app.add_typer(captions_app, name="captions")
    media_app.add_typer(audio_app, name="audio")
    media_app.add_typer(visual_app, name="visual")
    app.add_typer(media_app, name="media")


@media_app.command("status")
def status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Show media feature status without processing media files."""

    _, _, resolved_database_path, config = optional_config_runtime(config_path, database_path, project_local)
    conn = _connect_if_exists(resolved_database_path)
    try:
        status = get_media_status(config, conn)
    finally:
        if conn is not None:
            conn.close()
    table = Table(title="KGFS Media Status")
    table.add_column("Check")
    table.add_column("Value")
    table.add_row("Media enabled", str(status.enabled))
    table.add_row("Photo EXIF enabled", str(status.photo_metadata_enabled))
    table.add_row("EXIF dependency available", str(status.exif_available))
    table.add_row("Caption backend", f"{status.caption_backend} (available={status.caption_available})")
    table.add_row("Audio backend", f"{status.audio_backend} (available={status.audio_available})")
    table.add_row("Visual backend", f"{status.visual_backend} (available={status.visual_available})")
    table.add_row("Cloud OCR fallback", str(status.cloud_fallback_enabled))
    table.add_row("Media metadata rows", str(status.media_metadata_count))
    table.add_row("Media text rows", str(status.media_text_count))
    table.add_row("Media embedding rows", str(status.media_embedding_count))
    table.add_row("Media cache size", format_bytes(status.cache_size_bytes))
    for warning in status.warnings:
        table.add_row("Warning", warning)
    console.print(table)


@media_app.command("clear")
def clear_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    yes: bool = typer.Option(False, "--yes", help="Required confirmation."),
) -> None:
    """Clear KGFS media-derived data only."""

    if not yes:
        raise typer.BadParameter("Pass --yes to clear KGFS media metadata/text/embedding rows.")
    _, _, resolved_database_path, _ = runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        counts = clear_media_data(conn)
    finally:
        conn.close()
    console.print(
        "Cleared media data: "
        f"metadata={counts['media_metadata']}, text={counts['media_text']}, embeddings={counts['media_embeddings']}."
    )


@media_app.command("exif")
def exif_cmd(
    path: Path = typer.Argument(..., help="Image path to inspect without modifying it."),
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    """Read local image metadata and print a searchable preview."""

    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    image = path.expanduser()
    if not image.exists():
        raise typer.BadParameter(f"Image does not exist: {image}")
    try:
        metadata = extract_exif_metadata(image)
    except Exception as exc:
        console.print(str(exc))
        raise typer.Exit(code=2) from exc
    console.print(photo_metadata_text(metadata))
    if not config.media.photos.store_location_metadata:
        console.print("GPS/location metadata is not stored by default.")


@media_app.command("index")
def index_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
    photos: bool = typer.Option(False, "--photos", help="Index photo/EXIF metadata for indexed media files."),
    captions: bool = typer.Option(False, "--captions", help="Generate captions for indexed images."),
    audio: bool = typer.Option(False, "--audio", help="Transcribe indexed audio files."),
    visual: bool = typer.Option(False, "--visual", help="Generate visual embeddings for indexed images."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover/index without writing when supported."),
    allow_risky_root: bool = typer.Option(False, "--allow-risky-root", help="Allow risky root folders."),
) -> None:
    """Run media-aware indexing for explicitly configured folders."""

    _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
    if not config.media.enabled:
        console.print("Media indexing is disabled. Set media.enabled: true in config.yaml.")
        raise typer.Exit(code=2)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        summary = index_configured_folders(config, conn, dry_run=dry_run, allow_risky_root=allow_risky_root)
        photo_indexed = photo_failed = 0
        caption_indexed = caption_failed = 0
        audio_indexed = audio_failed = 0
        visual_indexed = visual_failed = 0
        if not dry_run and (photos or config.media.photos.enabled):
            photo_indexed, photo_failed = index_existing_photo_metadata(conn, config)
        if not dry_run and (captions or config.media.captions.enabled):
            caption_indexed, caption_failed = index_existing_captions(conn, config)
        if not dry_run and (audio or config.media.audio.transcription_enabled):
            audio_indexed, audio_failed = index_existing_transcripts(conn, config)
        if not dry_run and (visual or config.media.visual.enabled):
            visual_indexed, visual_failed = index_existing_visual_embeddings(conn, config)
    finally:
        conn.close()
    console.print(
        f"Discovered {summary.discovered}, indexed {summary.indexed}, skipped unchanged {summary.skipped_unchanged}, "
        f"failures {summary.failed}; photo metadata indexed {photo_indexed}, failures {photo_failed}; "
        f"captions indexed {caption_indexed}, failures {caption_failed}; "
        f"transcripts indexed {audio_indexed}, failures {audio_failed}; "
        f"visual embeddings indexed {visual_indexed}, failures {visual_failed}."
    )


@media_app.command("caption")
def caption_top_cmd(
    path: Path,
    config_path: Path | None = typer.Option(None, "--config"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    """Caption one image with the configured local caption backend."""

    _, _, _, config = optional_config_runtime(config_path, None, project_local)
    result = caption_image(path.expanduser(), config)
    console.print(result.text or result.error or result.status)


@media_app.command("transcribe")
def transcribe_top_cmd(
    path: Path,
    config_path: Path | None = typer.Option(None, "--config"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    """Transcribe one audio file with the configured local transcription backend."""

    _, _, _, config = optional_config_runtime(config_path, None, project_local)
    result = transcribe_audio(path.expanduser(), config)
    console.print(result.text or result.error or result.status)


@media_app.command("visual-similar")
def visual_similar_top_cmd(
    file_id: int = typer.Argument(..., help="Indexed file ID with a stored visual embedding."),
    config_path: Path | None = typer.Option(None, "--config"),
    database_path: Path | None = typer.Option(None, "--database"),
    project_local: bool = typer.Option(False, "--project-local"),
    limit: int = typer.Option(10, "--limit", min=1),
) -> None:
    """Find visually similar indexed files using stored local media embeddings."""

    _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        results = find_visual_similar(conn, file_id, config, limit=limit)
    finally:
        conn.close()
    table = Table(title="KGFS Visual Similarity")
    table.add_column("ID", justify="right")
    table.add_column("File")
    table.add_column("Score", justify="right")
    table.add_column("Snippet")
    for result in results:
        table.add_row(str(result.result_id), result.file_name, f"{result.score:.3f}", result.snippet)
    console.print(table)


@captions_app.command("status")
def captions_status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    status = get_caption_status(config)
    console.print(
        f"Captions enabled: {status.enabled}; backend={status.backend}; available={status.available}; {status.message}"
    )


@captions_app.command("caption")
def caption_cmd(
    path: Path,
    config_path: Path | None = typer.Option(None, "--config"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    _, _, _, config = optional_config_runtime(config_path, None, project_local)
    result = caption_image(path.expanduser(), config)
    console.print(result.text or result.error or result.status)


@captions_app.command("index")
def captions_index_cmd(
    config_path: Path | None = typer.Option(None, "--config"),
    database_path: Path | None = typer.Option(None, "--database"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        indexed, failed = index_existing_captions(conn, config)
    finally:
        conn.close()
    console.print(f"Caption rows indexed {indexed}, failures {failed}.")


@audio_app.command("status")
def audio_status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    status = get_audio_status(config)
    console.print(
        f"Audio enabled: {status.enabled}; backend={status.backend}; available={status.available}; {status.message}"
    )


@audio_app.command("transcribe")
def transcribe_cmd(
    path: Path,
    config_path: Path | None = typer.Option(None, "--config"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    _, _, _, config = optional_config_runtime(config_path, None, project_local)
    result = transcribe_audio(path.expanduser(), config)
    console.print(result.text or result.error or result.status)


@audio_app.command("index")
def audio_index_cmd(
    config_path: Path | None = typer.Option(None, "--config"),
    database_path: Path | None = typer.Option(None, "--database"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        indexed, failed = index_existing_transcripts(conn, config)
    finally:
        conn.close()
    console.print(f"Transcript rows indexed {indexed}, failures {failed}.")


@visual_app.command("status")
def visual_status_cmd(
    config_path: Path | None = typer.Option(None, "--config", help="Override config path."),
    database_path: Path | None = typer.Option(None, "--database", help="Override database path."),
    project_local: bool = typer.Option(False, "--project-local", help="Use .kgfs project-local paths."),
) -> None:
    _, _, _, config = optional_config_runtime(config_path, database_path, project_local)
    status = get_visual_status(config)
    console.print(
        f"Visual enabled: {status.enabled}; backend={status.backend}; available={status.available}; {status.message}"
    )


@visual_app.command("similar")
def visual_similar_cmd(
    file_id: int,
    config_path: Path | None = typer.Option(None, "--config"),
    database_path: Path | None = typer.Option(None, "--database"),
    project_local: bool = typer.Option(False, "--project-local"),
    limit: int = typer.Option(10, "--limit", min=1),
) -> None:
    visual_similar_top_cmd(file_id, config_path, database_path, project_local, limit)


@visual_app.command("index")
def visual_index_cmd(
    config_path: Path | None = typer.Option(None, "--config"),
    database_path: Path | None = typer.Option(None, "--database"),
    project_local: bool = typer.Option(False, "--project-local"),
) -> None:
    _, _, resolved_database_path, config = runtime(config_path, database_path, project_local)
    conn = connect_database(resolved_database_path)
    initialize_database(conn)
    try:
        indexed, failed = index_existing_visual_embeddings(conn, config)
    finally:
        conn.close()
    console.print(f"Visual embeddings indexed {indexed}, failures {failed}.")


def _connect_if_exists(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    try:
        conn = connect_database(path)
        initialize_database(conn)
        return conn
    except sqlite3.Error:
        return None
