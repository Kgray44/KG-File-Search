# KG File Search Agent Notes

KG File Search (KGFS) is a private, local-first Python app. Keep implementation choices cross-platform from the start.

## Safety Rules

- Never index a whole drive by default.
- Never delete, move, rename, or overwrite user files during indexing.
- Keep generated app data in platform-specific app directories unless project-local mode is explicitly enabled.
- Use `pathlib.Path` for paths.
- Keep platform-specific open/reveal behavior isolated in `kgfs/platform_utils.py`.
- Do not follow symlinks unless the config says to.
- Treat protected, system, application install, dependency, cache, and game install folders as ignored by default.

## Development

- Python 3.11+.
- Run tests with `python -m pytest`.
- Install locally with `python -m pip install -e ".[dev]"`.
- Prefer boring, readable code and tests that show the intended behavior.

