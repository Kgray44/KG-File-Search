"""Bounded local model backend benchmark helpers."""

from __future__ import annotations

import time

from kgfs.core.config import KGFSConfig
from kgfs.models.base import BackendBenchmarkResult
from kgfs.models.registry import collect_model_statuses


def benchmark_models(config: KGFSConfig) -> list[BackendBenchmarkResult]:
    """Return lightweight status-timing rows without running heavy models by default."""

    rows: list[BackendBenchmarkResult] = []
    for status in collect_model_statuses(config):
        start = time.perf_counter()
        elapsed = (time.perf_counter() - start) * 1000
        note = status.message
        if status.download_enabled:
            note += " Downloads are enabled for this backend."
        rows.append(
            BackendBenchmarkResult(
                name=status.name,
                kind=status.kind,
                available=status.available,
                elapsed_ms=elapsed,
                notes=note,
            )
        )
    return rows
