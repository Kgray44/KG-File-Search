# Examples

These examples use only behavior implemented in the current worktree.

## Example 1: Basic Local Index

```bash
python -m pip install -e ".[dev]"
kgfs init
kgfs add-folder "~/Documents/School Notes"
kgfs index
kgfs search "op amp circuit"
kgfs open 1
```

What happens:

- `init` creates config and app dirs.
- `add-folder` writes the folder to `indexed_folders`.
- `index` discovers supported files, extracts text, and writes SQLite rows.
- `search` queries SQLite FTS5 and saves latest result IDs.
- `open 1` opens the first latest result.

Sources: `kgfs/cli/commands/init.py`, `kgfs/cli/commands/folders.py`, `kgfs/cli/commands/index.py`, `kgfs/cli/commands/search.py`, `kgfs/cli/commands/open_reveal.py`.

## Example 2: Project-Local Test Corpus

```bash
mkdir sample-files
printf "Motor torque lab report" > sample-files/notes.md

kgfs init --project-local
kgfs add-folder "./sample-files" --project-local
kgfs index --project-local
kgfs search "motor torque" --project-local
kgfs stats --project-local
```

Project-local files live under `.kgfs/` in the current directory.

Source: `kgfs/core/app_dirs.py`.

## Example 3: Use Explicit Config and Database Paths

```bash
kgfs init --config ./config.yaml
kgfs add-folder "./docs" --config ./config.yaml
kgfs index --config ./config.yaml --database ./kgfs.sqlite3
kgfs search "pid control" --config ./config.yaml --database ./kgfs.sqlite3
```

Source: `kgfs/core/app_dirs.py`, `kgfs/cli/shared.py`.

## Example 4: Filtered Search

```bash
kgfs search "pid" --ext .pdf
kgfs search "pid" --type pdf
kgfs search "pid" --folder "Controls"
kgfs search "pid" --after 2025-01-01 --before 2025-12-31
kgfs search "failed extraction" --failed-only
```

Filter behavior source: `kgfs/search/filters.py`.

## Example 5: Reindex When Metadata Is Not Enough

If a file changed but size and modified time look unchanged:

```bash
kgfs index --verify-hashes
```

If you want to re-extract every discovered file:

```bash
kgfs index --force
```

Sources: `kgfs/indexing/indexer.py`, `tests/test_indexing.py`.

## Example 6: Prune Deleted Files

Show stale database records without changing the DB:

```bash
kgfs prune --dry-run
```

Remove stale rows and related FTS/chunk/latest-result rows:

```bash
kgfs prune
```

Source: `kgfs/indexing/prune.py`.

## Example 7: Semantic Search

Install semantic support:

```bash
python -m pip install -e ".[semantic]"
```

Enable in config:

```yaml
semantic:
  enabled: true
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size_chars: 1200
  chunk_overlap_chars: 200
  local_files_only: true
  batch_size: 16
```

Build chunks:

```bash
kgfs semantic-index --rebuild
```

Search:

```bash
kgfs semantic "rotational force"
kgfs search "rotational force" --mode semantic
kgfs search "rotational force" --hybrid
```

Sources: `kgfs/cli/commands/semantic.py`, `kgfs/search/semantic.py`.

## Example 8: AI Preview Without API Call

Enable AI in config for preview:

```yaml
ai:
  enabled: true
  require_confirmation: true
  preview_context_before_send: true
```

Preview answer context:

```bash
kgfs ask "What do my notes say about op-amps?" --preview-ai-context
```

Preview rerank context:

```bash
kgfs search "speaker crossover" --ai-rerank --preview-ai-context
```

No API call is made when `--preview-ai-context` is used.

Sources: `kgfs/cli/shared.py`, `kgfs/cli/commands/search.py`, `tests/test_cli.py`.

## Example 9: OpenAI Answer Synthesis

Install OpenAI dependency:

```bash
python -m pip install -e ".[openai]"
```

Set API key:

```bash
export OPENAI_API_KEY="sk-..."
```

Enable AI:

```yaml
ai:
  enabled: true
  require_confirmation: true
  send_file_paths: false
  send_full_file_text: false
  redact_home_path: true
```

Ask:

```bash
kgfs ask "What do my notes say about motor torque?"
```

Source: `kgfs/ai.py`.

## Example 10: Start Web Dashboard

```bash
kgfs web
```

Open:

```text
http://127.0.0.1:8765
```

Use `/search?q=pid&ext=.pdf` for a filtered search URL.

Sources: `kgfs/cli/commands/web.py`, `kgfs/web/app.py`.

## Example 11: Reset and Rebuild

Dry-run reset:

```bash
kgfs reset-index --dry-run
```

Reset database files:

```bash
kgfs reset-index --yes
```

Reset and index again:

```bash
kgfs rebuild --yes
```

Sources: `kgfs/reset.py`, `kgfs/cli/commands/maintenance.py`.

## Example 12: Build a Package

```bash
python -m pip install -e ".[package]"
python scripts/build_package.py --clean --mode onedir
python scripts/smoke_test_packaged.py --package dist-packages/KGFS
```

Expected artifact:

```text
dist-packages/KGFS-<os>-<arch>.zip
```

Sources: `scripts/build_package.py`, `scripts/smoke_test_packaged.py`.
