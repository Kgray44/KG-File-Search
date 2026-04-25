"""Optional hnswlib backend scaffold."""

from __future__ import annotations

from kgfs.search.backends._optional import OptionalArtifactVectorBackend


class HnswVectorBackend(OptionalArtifactVectorBackend):
    name = "hnsw"
    module_name = "hnswlib"
    package_name = "hnswlib"
    install_hint = 'Install hnswlib support with: python -m pip install -e ".[hnsw]"'
    config_section = "hnsw"
