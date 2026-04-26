"""Recommendation helpers for optional local model backends."""

from __future__ import annotations

from dataclasses import dataclass, field

from kgfs.core.config import KGFSConfig
from kgfs.models.registry import collect_model_statuses


@dataclass(frozen=True)
class ModelRecommendation:
    recommended: str
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def recommend_models(config: KGFSConfig) -> ModelRecommendation:
    statuses = collect_model_statuses(config)
    warnings = [f"{status.kind}:{status.name} has downloads enabled." for status in statuses if status.download_enabled]
    ready = [status for status in statuses if status.readiness == "ready"]
    configured_missing = [
        status
        for status in statuses
        if status.enabled
        and status.readiness in {"missing_dependency", "missing_model", "configuration_needed", "error"}
    ]
    for status in configured_missing:
        warnings.append(f"{status.kind}:{status.name} is enabled but readiness is {status.readiness}.")
    if not config.ocr.enabled and not config.media.enabled:
        return ModelRecommendation(
            "Keep base local text search plus Tesseract when OCR is needed.",
            [
                "Advanced OCR/media model backends are disabled by default.",
                "Tesseract is the simplest local OCR path when OCR is needed.",
                "metadata-caption is the safe media caption baseline because it uses filename/metadata only.",
                "bytehash-visual is useful for plumbing tests only; it is not visual understanding.",
            ],
            warnings,
        )
    available = [f"{status.kind}:{status.name}" for status in ready]
    return ModelRecommendation(
        ", ".join(available) if available else "No advanced local model backend is ready.",
        [
            "Install optional extras only for the media/OCR workflows you actually use.",
            "Configure local model paths before enabling backends that normally fetch model files.",
            "Use kgfs models validate BACKEND and kgfs models config-snippet BACKEND before indexing media at scale.",
        ],
        warnings,
    )
