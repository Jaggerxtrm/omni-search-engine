# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This repository now centers on **vaultctl**, a local-first CLI and MCP adapter layer for knowledge retrieval and vault operations.

- Search/index backend: **SQLite FTS5 + BM25** (`unicode61` tokenizer)
- Runtime: Python CLI (`vaultctl`) and stdio MCP bridge
- Legacy MCP compatibility: old tool names are preserved via adapters in `src/vaultctl/mcp/adapters.py`
- Default config: `~/.config/vaultctl/config.toml`
- Default database: `~/.local/share/vaultctl/index.db`

## Architecture
- **CLI entrypoint**: `src/vaultctl/cli/app.py`
- **Services**: `src/vaultctl/services/` (`search_service`, `index_service`, `note_service`, `inspect_service`, `stats_service`, `audit_service`)
- **Storage**: `src/vaultctl/store/` (SQLite connection, indexer, FTS queries, stats/audit)
- **Ingestion**: `src/vaultctl/ingest/` (markdown/transcript parsing and source iteration)
- **Config + paths**: `src/vaultctl/core/config.py`, `src/vaultctl/core/paths.py`, `src/vaultctl/core/models.py`
- **MCP adapter bridge**: `src/vaultctl/mcp/server.py`, `src/vaultctl/mcp/adapters.py`

## Configuration
vaultctl reads TOML config from:

- `~/.config/vaultctl/config.toml`

Minimal example:

```toml
db_path = "~/.local/share/vaultctl/index.db"

[[sources]]
id = "vault"
root = "~/second-mind"
include_glob = "**/*.md"
exclude_glob = "**/.obsidian/**"

[[sources]]
id = "transcripts"
root = "~/dev/transcriptoz/transcripts"
include_glob = "*.analysis.md"
```

If config is missing, defaults are loaded in `src/vaultctl/core/config.py`.

## CLI usage
Primary commands (see `build_parser()` in `src/vaultctl/cli/app.py`):

```bash
vaultctl search "query" [--source <id>] [--folder <path>] [--tag <tag>] [--status <value>] [-n 5] [--json]
vaultctl index [--source <id>] [--full] [--json]
vaultctl watch [--source <id>] [--debounce-ms 1000] [--json]
vaultctl status [--json]

vaultctl note read <path> [--source <id>] [--json]
vaultctl note write <path> <content> [--source <id>] [--json]
vaultctl note append <path> <content> [--source <id>] [--json]
vaultctl note delete <path> [--source <id>] [--json]
vaultctl note index <path> [--source <id>] [--json]
vaultctl note links <path> [--source <id>] [--json]

vaultctl find <pattern> [--source <id>] [--root <path>] [-n 20] [--json]
vaultctl tree [root] [--source <id>] [--depth <n>] [--json]
vaultctl context <target> [--json]
vaultctl stats [--json]
vaultctl audit orphans|linked|duplicates [--source <id>] [-n 20] [--json]

vaultctl mcp serve --transport stdio
```

## Replacing old MCP calls
Old MCP tool names continue to work through adapters (`legacy_tool_adapters()`), but new work should prefer direct CLI usage where possible.

Examples:

- Old `semantic_search(query, n_results=5)` → `vaultctl search "query" -n 5 --json`
- Old `reindex_vault(force=True)` → `vaultctl index --full --json`
- Old `get_index_stats()` → `vaultctl status --json`
- Old `get_vault_statistics()` → `vaultctl stats --json`
- Old `search_notes(query, n_results=5)` → `vaultctl search "query" -n 5 --json`
- Old `get_vault_structure(root_path,max_depth)` → `vaultctl tree <root_path> --depth <max_depth> --json`

Full legacy mappings are defined in `src/vaultctl/mcp/adapters.py`.

## Development notes
- Install package in editable mode for local CLI work: `pip install -e .`
- Entry point is declared in `pyproject.toml`: `vaultctl = "vaultctl.cli.app:main"`
- Prefer `--json` output for scripted/agent workflows.
- Keep docs and adapter mappings in sync when introducing/removing tools.
