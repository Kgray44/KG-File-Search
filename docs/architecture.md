# KGFS Architecture

KG File Search is organized around a small set of boring packages. The goal is
to keep runtime behavior local-first while making future growth easier to place.

## Package Layout

```text
kgfs/
  __main__.py
  cli/          Typer application and command modules
  core/         Shared config, path, platform, resource, and model helpers
  db/           SQLite connection, schema, migrations, repositories, stats
  indexing/     Discovery, filtering, hashing, indexing, pruning
  search/       FTS queries, filters, ranking, snippets, semantic/hybrid search
  extractors/   Text extraction by file type
  web/          FastAPI dashboard, templates, and static files
```

Compatibility modules may re-export public functions from the older flat module
paths while internal code moves to the package layout.

## Where To Add Things

- Add new CLI commands under `kgfs/cli/commands/` and register them from
  `kgfs/cli/app.py`.
- Add general shared helpers under `kgfs/core/`.
- Add SQLite schema changes in `kgfs/db/schema.py` and versioned migration logic
  in `kgfs/db/migrations.py`.
- Add new indexing behavior under `kgfs/indexing/`.
- Add new search modes under `kgfs/search/`.
- Add new file extractors under `kgfs/extractors/`.
- Add web dashboard routes under `kgfs/web/`.
- Add packaging changes under `packaging/` and cross-platform scripts under
  `scripts/`.

## Boundaries

- Core modules should not depend on Typer or FastAPI.
- Database modules should not open, move, rename, or delete user source files.
- Prune/reset behavior may delete KGFS index data only.
- Semantic search stays optional and local.
- AI Assist stays opt-in and downstream of local search.
