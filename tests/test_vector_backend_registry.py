from __future__ import annotations

import sys

import pytest

from kgfs.search.backends.registry import (
    UnknownVectorBackend,
    get_vector_backend,
    list_vector_backend_names,
    vector_backend_install_hint,
)


def test_default_vector_registry_lists_known_backends() -> None:
    assert list_vector_backend_names() == ["sqlite_scan", "sqlite_vec", "hnsw", "faiss"]


def test_sqlite_scan_resolves_successfully() -> None:
    backend = get_vector_backend("sqlite_scan")

    assert backend.name == "sqlite_scan"


def test_unknown_vector_backend_message_lists_valid_names() -> None:
    with pytest.raises(UnknownVectorBackend, match="Valid backends: sqlite_scan, sqlite_vec, hnsw, faiss"):
        get_vector_backend("mystery")


def test_optional_backend_hints_do_not_import_heavy_dependencies() -> None:
    for module_name in ("sqlite_vec", "hnswlib", "faiss"):
        sys.modules.pop(module_name, None)

    assert "sqlite-vec" in vector_backend_install_hint("sqlite_vec")
    assert "hnswlib" in vector_backend_install_hint("hnsw")
    assert "faiss-cpu" in vector_backend_install_hint("faiss")
    assert "sqlite_vec" not in sys.modules
    assert "hnswlib" not in sys.modules
    assert "faiss" not in sys.modules
