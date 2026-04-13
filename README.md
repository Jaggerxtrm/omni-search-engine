# vaultctl (omni-search-engine)

Local-first search and vault operations for markdown knowledge bases, now powered by **vaultctl**.

> This project replaced the old ChromaDB/OpenAI/FastMCP stack with a SQLite FTS5/BM25 backend and a CLI-first workflow.

## What changed

- ✅ Replaced vector/embedding stack with SQLite FTS5 (`unicode61`) + BM25 ranking
- ✅ Added CLI-first interface (`vaultctl ...`)
- ✅ Kept backward compatibility for legacy MCP tool names via `src/vaultctl/mcp/adapters.py`
- ✅ Standardized config at `~/.config/vaultctl/config.toml`
- ✅ Standardized DB path at `~/.local/share/vaultctl/index.db`

## Install

```bash
pip install -e .
```

This exposes the `vaultctl` command from `pyproject.toml`.

## Configuration

Create `~/.config/vaultctl/config.toml`:

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

Notes:
- `[[sources]]` must be non-empty if config file exists.
- If the config file is absent, vaultctl falls back to defaults from `src/vaultctl/core/config.py`.

## CLI quickstart

```bash
# index all configured sources
vaultctl index --json

# run a search
vaultctl search "hybrid retrieval" -n 8 --json

# inspect corpus state
vaultctl status --json
vaultctl stats --json

# content discovery helpers
vaultctl find "planner" --source vault -n 20 --json
vaultctl tree --source vault --depth 3 --json
vaultctl context "notes/roadmap.md" --json

# note operations
vaultctl note read "notes/todo.md" --source vault --json
vaultctl note append "notes/todo.md" "\n- finish migration" --source vault --json

# audits
vaultctl audit orphans --source vault -n 50 --json
```

## Run as MCP bridge (legacy clients)

For clients expecting MCP-style tool invocation, run:

```bash
vaultctl mcp serve --transport stdio
```

The bridge serves legacy tool names using adapter functions in `src/vaultctl/mcp/adapters.py`.

## Migration guide: old MCP calls → vaultctl

Use this mapping when replacing old calls:

| Old MCP call | New vaultctl command |
|---|---|
| `semantic_search(query, n_results=5)` | `vaultctl search "<query>" -n 5 --json` |
| `search_notes(query, n_results=5)` | `vaultctl search "<query>" -n 5 --json` |
| `reindex_vault(force=True)` | `vaultctl index --full --json` |
| `get_index_stats()` | `vaultctl status --json` |
| `get_vault_statistics()` | `vaultctl stats --json` |
| `get_full_context(parent_id)` | `vaultctl context "<parent_id>" --json` |
| `get_vault_structure(root_path, max_depth)` | `vaultctl tree "<root_path>" --depth <max_depth> --json` |
| `read_note(note_path)` | `vaultctl note read "<note_path>" --json` |
| `write_note(note_path, content)` | `vaultctl note write "<note_path>" "<content>" --json` |
| `append_to_note(note_path, content)` | `vaultctl note append "<note_path>" "<content>" --json` |
| `delete_note(note_path)` | `vaultctl note delete "<note_path>" --json` |
| `get_orphaned_notes()` | `vaultctl audit orphans --json` |
| `get_most_linked_notes(n_results=10)` | `vaultctl audit linked -n 10 --json` |
| `get_duplicate_content(...)` | `vaultctl audit duplicates --json` |

## Code layout (current)

- `src/vaultctl/cli/` — CLI commands and argument parsing
- `src/vaultctl/services/` — business logic
- `src/vaultctl/store/` — SQLite, indexing, FTS query execution
- `src/vaultctl/ingest/` — markdown/transcript parsing
- `src/vaultctl/mcp/` — stdio MCP adapter bridge and legacy mappings

## Development

```bash
# format/lint/typecheck (project tooling)
ruff check .
mypy src
```

(Use project-specific CI scripts if available.)
