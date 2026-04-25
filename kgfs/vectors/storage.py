"""Backend artifact storage helpers."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from kgfs.core.config import KGFSConfig


def vector_backends_root(config: KGFSConfig) -> Path:
    if config.database_path is not None:
        return config.database_path.expanduser().parent / "vector-backends"
    return Path.cwd() / ".kgfs" / "vector-backends"


def backend_artifact_dir(config: KGFSConfig, backend_name: str, *, model_name: str | None = None) -> Path:
    root = vector_backends_root(config)
    if model_name:
        model_key = hashlib.sha256(model_name.encode("utf-8")).hexdigest()[:16]
        return root / backend_name / model_key
    return root / backend_name


def clear_backend_artifacts(config: KGFSConfig, backend_name: str, *, model_name: str | None = None) -> int:
    target = backend_artifact_dir(config, backend_name, model_name=model_name)
    if not target.exists():
        return 0
    root = vector_backends_root(config).resolve()
    resolved = target.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"Refusing to clear vector artifacts outside KGFS vector storage: {resolved}")
    if target.is_file():
        target.unlink()
        return 1
    count = sum(1 for _ in target.rglob("*"))
    shutil.rmtree(target)
    return count
