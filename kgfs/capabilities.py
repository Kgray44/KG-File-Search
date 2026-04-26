"""Feature capability summaries for release/readiness diagnostics."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from importlib.util import find_spec

from kgfs.core.config import KGFSConfig
from kgfs.db.schema import check_fts5_available, initialize_database
from kgfs.integrations.status import get_integration_status
from kgfs.media.status import get_media_status
from kgfs.models.registry import collect_model_statuses
from kgfs.ocr.status import get_ocr_status
from kgfs.search.backends import list_vector_backend_names
from kgfs.search.semantic import get_semantic_status
from kgfs.vectors.status import get_vector_status
from kgfs.version import __version__


@dataclass(frozen=True)
class CapabilityRow:
    feature: str
    status: str
    details: str


def collect_capabilities(config: KGFSConfig) -> list[CapabilityRow]:
    """Return local feature availability without touching user source files."""

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    initialize_database(conn)
    try:
        vector_status = get_vector_status(conn, config)
        ocr_status = get_ocr_status(config, conn)
        media_status = get_media_status(config, conn)
    finally:
        conn.close()

    semantic = get_semantic_status(config.semantic)
    openai_available = find_spec("openai") is not None
    integrations = get_integration_status()
    supported_integrations = [item.name for item in integrations if item.supported and item.scaffold_available]
    model_statuses = collect_model_statuses(config)
    ready_models = [f"{item.kind}:{item.name}" for item in model_statuses if item.available]
    configured_models = [f"{item.kind}:{item.name}" for item in model_statuses if item.enabled]

    return [
        CapabilityRow(
            "KGFS version",
            __version__,
            "Version source: kgfs.version.",
        ),
        CapabilityRow(
            "Keyword search",
            "available" if check_fts5_available() else "unavailable",
            "SQLite FTS5 keyword search is built in.",
        ),
        CapabilityRow(
            "Semantic search",
            _enabled_status(config.semantic.enabled, semantic.available),
            semantic.message,
        ),
        CapabilityRow(
            "Vector backends",
            "available" if vector_status.backend_available else "unavailable",
            f"Configured: {vector_status.backend_name}; known: {', '.join(list_vector_backend_names())}.",
        ),
        CapabilityRow(
            "OCR",
            _enabled_status(config.ocr.enabled, ocr_status.available),
            f"Backend: {ocr_status.backend_name}; {ocr_status.message}",
        ),
        CapabilityRow(
            "Media",
            "enabled" if media_status.enabled else "disabled",
            (
                f"Photo EXIF: {media_status.photo_metadata_enabled}; captions/audio/visual: "
                f"{media_status.caption_backend}/{media_status.audio_backend}/{media_status.visual_backend}."
            ),
        ),
        CapabilityRow(
            "Local model backends",
            "configured" if configured_models else "disabled",
            f"Ready: {', '.join(ready_models) or 'none'}; downloads disabled by default.",
        ),
        CapabilityRow(
            "AI Assist",
            _enabled_status(config.ai.enabled, openai_available),
            f"Provider: {config.ai.provider}; API key comes from {config.ai.api_key_env}.",
        ),
        CapabilityRow(
            "Local API",
            "enabled" if config.api.enabled else "disabled",
            f"Bind: {config.api.host}:{config.api.port}; token required: {config.api.require_token}.",
        ),
        CapabilityRow(
            "TUI",
            _enabled_status(config.ui.tui_enabled, find_spec("textual") is not None),
            "Textual dependency is optional and imported only by the TUI command.",
        ),
        CapabilityRow(
            "Tray and integrations",
            "enabled" if config.integrations.enabled else "disabled",
            f"Supported scaffolds on this OS: {', '.join(supported_integrations) or 'none'}.",
        ),
    ]


def _enabled_status(enabled: bool, available: bool) -> str:
    if not enabled:
        return "disabled"
    return "available" if available else "unavailable"
