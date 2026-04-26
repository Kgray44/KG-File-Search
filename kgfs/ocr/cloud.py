"""Cloud OCR fallback scaffold with strict no-upload defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kgfs.core.config import KGFSConfig


@dataclass(frozen=True)
class CloudOCRPlan:
    allowed: bool
    message: str
    provider: str | None
    preview: dict[str, object] = field(default_factory=dict)


def build_cloud_ocr_plan(path: Path, config: KGFSConfig, *, allow_cloud: bool, confirmed: bool) -> CloudOCRPlan:
    settings = config.ocr.cloud_fallback
    preview = {
        "path": str(path),
        "provider": settings.provider,
        "would_upload": False,
    }
    if not settings.enabled:
        return CloudOCRPlan(False, "Cloud OCR fallback is disabled.", settings.provider, preview)
    if not settings.provider:
        return CloudOCRPlan(False, "Cloud OCR provider is not configured.", settings.provider, preview)
    if not allow_cloud:
        return CloudOCRPlan(False, "Cloud OCR requires an explicit --allow-cloud flag.", settings.provider, preview)
    if settings.require_confirmation and not confirmed:
        return CloudOCRPlan(False, "Cloud OCR requires explicit confirmation before upload.", settings.provider, preview)
    preview["would_upload"] = True
    return CloudOCRPlan(
        False,
        f"Cloud OCR provider '{settings.provider}' is not implemented in this phase.",
        settings.provider,
        preview,
    )
