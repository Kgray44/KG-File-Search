"""Status helpers for optional local model backends."""

from __future__ import annotations

from kgfs.core.config import KGFSConfig
from kgfs.models.base import BackendStatus
from kgfs.models.registry import collect_model_statuses


def get_model_status(config: KGFSConfig) -> list[BackendStatus]:
    return collect_model_statuses(config)
