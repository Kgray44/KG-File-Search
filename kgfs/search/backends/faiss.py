"""Optional FAISS backend scaffold."""

from __future__ import annotations

from kgfs.search.backends._optional import OptionalArtifactVectorBackend


class FaissVectorBackend(OptionalArtifactVectorBackend):
    name = "faiss"
    module_name = "faiss"
    package_name = "faiss-cpu"
    install_hint = 'Install faiss-cpu support with: python -m pip install -e ".[faiss]"'
    config_section = "faiss"
