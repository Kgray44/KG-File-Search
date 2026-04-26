"""Alfred scaffold export."""

from __future__ import annotations

from pathlib import Path


def export_alfred(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    script = output / "kgfs-search.sh"
    readme = output / "README.md"
    script.write_text(
        """#!/usr/bin/env bash
# Alfred script filter scaffold for KGFS.
kgfs search "$1" --mode auto
""",
        encoding="utf-8",
    )
    readme.write_text(
        "# KGFS Alfred Scaffold\n\nCreate an Alfred workflow that passes the query to `kgfs-search.sh`.\n",
        encoding="utf-8",
    )
    return [script, readme]
