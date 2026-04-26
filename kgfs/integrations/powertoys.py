"""PowerToys Run scaffold export."""

from __future__ import annotations

from pathlib import Path


def scaffold_powertoys(output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    readme = output / "README.md"
    manifest = output / "kgfs-powertoys-scaffold.json"
    readme.write_text(
        "# KGFS PowerToys Run Scaffold\n\nThis phase does not compile or install a plugin. Use this scaffold as notes for a future PowerToys Run plugin that shells out to `kgfs search` locally.\n",
        encoding="utf-8",
    )
    manifest.write_text('{"name":"KGFS","command":"kgfs search {query} --mode auto"}\n', encoding="utf-8")
    return [readme, manifest]
