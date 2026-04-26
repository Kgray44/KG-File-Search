"""Finder Quick Action scaffold export."""

from __future__ import annotations

from pathlib import Path


def scaffold_finder(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    script = output / "kgfs-finder-search.sh"
    readme = output / "README.md"
    script.write_text(
        """#!/usr/bin/env bash
# Finder Quick Action scaffold. Pass selected text/query to KGFS.
kgfs search "$1" --mode auto
""",
        encoding="utf-8",
    )
    readme.write_text(
        "# KGFS Finder Scaffold\n\nCreate an Automator Quick Action manually and point it at `kgfs-finder-search.sh`.\n",
        encoding="utf-8",
    )
    return [script, readme]
