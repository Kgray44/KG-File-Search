"""Shared KGFS quickstart text."""

from __future__ import annotations

from kgfs.version import __version__


def build_quickstart_text(*, executable_name: str = "kgfs", packaged: bool = False, version: str = __version__) -> str:
    """Return a safe first-run guide for CLI and packaged builds."""

    package_note = (
        "This packaged build stores config/data/cache in the normal platformdirs locations for your OS. "
        "The package does not include your config, database, cache, logs, model caches, API keys, or indexed files."
        if packaged
        else "Project-local mode stores config/data/cache under .kgfs/ in the current directory."
    )
    return f"""KG File Search (KGFS) {version} quickstart

KGFS is private, local-first file search. It indexes only folders you choose.
Generated config starts with indexed_folders: [].
KGFS never indexes the whole drive by default.

Check the build:
  {executable_name} version
  {executable_name} doctor
  {executable_name} capabilities

Safe first run:
  {executable_name} init
  {executable_name} doctor
  {executable_name} add-folder "./sample-files"
  {executable_name} index
  {executable_name} search "motor torque"

Try the artificial demo corpus from the repository:
  {executable_name} init --project-local
  {executable_name} add-folder "./examples/sample-corpus" --project-local
  {executable_name} index --project-local
  {executable_name} search "motor torque" --project-local

{package_note}
"""
