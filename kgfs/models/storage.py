"""Local model cache path helpers."""

from __future__ import annotations

from pathlib import Path

from kgfs.core.app_dirs import AppPaths
from kgfs.core.config import KGFSConfig


def model_cache_dir(config: KGFSConfig, app_paths: AppPaths, backend_name: str | None = None) -> Path:
    root = config.models.cache_dir or (app_paths.cache_dir / "models")
    return root / backend_name if backend_name else root
