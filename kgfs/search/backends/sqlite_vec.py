"""Optional sqlite-vec backend scaffold."""

from __future__ import annotations

from kgfs.search.backends._optional import OptionalArtifactVectorBackend


class SqliteVecVectorBackend(OptionalArtifactVectorBackend):
    name = "sqlite_vec"
    module_name = "sqlite_vec"
    package_name = "sqlite-vec"
    install_hint = 'Install sqlite-vec support with: python -m pip install -e ".[sqlite-vec]"'
    config_section = "sqlite_vec"
    experimental = True
