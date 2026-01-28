---
title: SSOT API Architecture (MCP Tools)
version: 0.4.0
updated: 2026-01-24T22:55:00+01:00
scope: infra
category: infra
subcategory: api
domain: [infra, api, mcp]
changelog:
  - 0.4.0 (2026-01-24): Added `source` filter to semantic_search and new analytics tools.
  - 0.3.0 (2026-01-22): Added file operations tools (read_note, write_note, append_to_note, delete_note)
  - 0.2.0 (2026-01-16): Updated tools to reflect AsyncIO implementation
  - 0.1.0 (2026-01-16): Initial documentation of MCP tools
---

## Exposed Tools

The server exposes the following MCP tools to clients. All tools are implemented as `async` functions to ensure non-blocking operation.

### 1. `semantic_search`
- **Type**: Async
- **Purpose**: Retrieve notes semantically matching a query.
- **Inputs**: 
    - `query` (str)
    - `n_results` (int)
    - `folder` (opt)
    - `tags` (opt)
    - `source` (opt): ID of the source to search (e.g., "vault", "current_project").
- **Output**: List of matches with similarity scores and metadata.
- **Logic**: Embeds query -> Searches VectorStore (with Filter) -> Reranks (FlashRank).

### 2. `reindex_vault`
- **Type**: Async
- **Purpose**: Manually trigger indexing for all sources.
- **Inputs**: `force` (bool).
- **Output**: Statistics (processed, skipped, duration).
- **Logic**: Delegates to `VaultIndexer.index_vault()`, iterating all configured sources.

### 3. `get_index_stats`
- **Type**: Async
- **Purpose**: Diagnostic information about the index.
- **Inputs**: None.
- **Output**: Total chunks, files, paths, model info.

### 4. `suggest_links`
- **Type**: Async
- **Purpose**: AI-assisted note linking.
- **Inputs**: `note_path`, `n_suggestions`, `min_similarity`, `exclude_current`.
- **Output**: List of candidate files to link to.

### 5. `index_note`
- **Type**: Async
- **Purpose**: Index a single file on demand.
- **Inputs**: `note_path` (str).
- **Output**: Success status and chunk count.

### 6. `search_notes`
- **Type**: Async
- **Purpose**: Regex-based file finding.
- **Inputs**: `pattern` (regex), `root_path` (opt).
- **Output**: List of matching file paths.

### 7. `get_vault_structure`
- **Type**: Async
- **Purpose**: Directory tree visualization.
- **Inputs**: `root_path`, `depth`.
- **Output**: Nested dictionary representing file structure.

### 8. `read_note`
- **Type**: Async
- **Purpose**: Read content and metadata of a note from the vault.
- **Inputs**: `note_path` (str).
- **Output**: Full content, metadata (tags, wikilinks, folder, file stats).
- **Use Case**: Cross-codebase access to vault notes.

### 9. `write_note`
- **Type**: Async
- **Purpose**: Create or overwrite a note in the vault.
- **Inputs**: `note_path` (str), `content` (str), `create_dirs` (bool, default: True).
- **Output**: Success status, creation flag, size, chunks indexed.
- **Logic**: Validates path → Creates directories if needed → Writes file → Auto-indexes.

### 10. `append_to_note`
- **Type**: Async
- **Purpose**: Append content to an existing note.
- **Inputs**: `note_path` (str), `content` (str).
- **Output**: Success status, size, chunks indexed.

### 11. `delete_note`
- **Type**: Async
- **Purpose**: Delete a note from filesystem and vector index.
- **Inputs**: `note_path` (str).
- **Output**: Success status and deleted flag.

### 12. `get_orphaned_notes`
- **Type**: Async
- **Purpose**: Find notes with zero incoming links.
- **Output**: List of orphaned notes.

### 13. `get_most_linked_notes`
- **Type**: Async
- **Purpose**: Find most cited notes.
- **Inputs**: `n_results` (int).
- **Output**: List of notes sorted by degree.

### 14. `get_duplicate_content`
- **Type**: Async
- **Purpose**: Find semantic duplicates.
- **Inputs**: `similarity_threshold` (float).
- **Output**: List of overlapping note pairs.

## Transport Modes
- **Stdio**: Default for local CLI use (Claude Desktop).
- **SSE**: Server-Sent Events for remote/persistent deployment (`--sse` flag).
