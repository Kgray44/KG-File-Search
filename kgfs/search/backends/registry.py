"""Lazy vector backend registry."""

from __future__ import annotations

from dataclasses import dataclass

from kgfs.search.backends.base import BackendAvailability, VectorBackend


class UnknownVectorBackend(ValueError):
    """Raised when a configured vector backend is unknown."""


@dataclass(frozen=True)
class VectorBackendDescriptor:
    name: str
    import_path: str
    class_name: str
    install_hint: str
    experimental: bool = False

    def create(self) -> VectorBackend:
        module = __import__(self.import_path, fromlist=[self.class_name])
        backend_cls = getattr(module, self.class_name)
        return backend_cls()


_BACKENDS: dict[str, VectorBackendDescriptor] = {
    "sqlite_scan": VectorBackendDescriptor(
        name="sqlite_scan",
        import_path="kgfs.search.backends.sqlite_scan",
        class_name="SqliteScanVectorBackend",
        install_hint="sqlite_scan is built into KGFS.",
    ),
    "sqlite_vec": VectorBackendDescriptor(
        name="sqlite_vec",
        import_path="kgfs.search.backends.sqlite_vec",
        class_name="SqliteVecVectorBackend",
        install_hint='Install sqlite-vec support with: python -m pip install -e ".[sqlite-vec]"',
        experimental=True,
    ),
    "hnsw": VectorBackendDescriptor(
        name="hnsw",
        import_path="kgfs.search.backends.hnsw",
        class_name="HnswVectorBackend",
        install_hint='Install hnswlib support with: python -m pip install -e ".[hnsw]"',
    ),
    "faiss": VectorBackendDescriptor(
        name="faiss",
        import_path="kgfs.search.backends.faiss",
        class_name="FaissVectorBackend",
        install_hint='Install faiss-cpu support with: python -m pip install -e ".[faiss]"',
    ),
}


def list_vector_backend_names() -> list[str]:
    return list(_BACKENDS)


def vector_backend_install_hint(name: str) -> str:
    normalized = normalize_backend_name(name)
    descriptor = _BACKENDS.get(normalized)
    if descriptor is None:
        return _unknown_message(name)
    return descriptor.install_hint


def get_vector_backend(name: str) -> VectorBackend:
    normalized = normalize_backend_name(name)
    descriptor = _BACKENDS.get(normalized)
    if descriptor is None:
        raise UnknownVectorBackend(_unknown_message(name))
    return descriptor.create()


def backend_availability_by_name(context) -> dict[str, BackendAvailability]:
    availability: dict[str, BackendAvailability] = {}
    for name in list_vector_backend_names():
        backend = get_vector_backend(name)
        availability[name] = backend.available(context)
    return availability


def normalize_backend_name(name: str) -> str:
    return str(name).strip().lower().replace("-", "_")


def _unknown_message(name: str) -> str:
    return f"Unknown vector backend: {name}. Valid backends: {', '.join(list_vector_backend_names())}."
