---
title: SSOT API Architecture (MCP Tools)
version: 0.3.0
updated: 2026-01-22T00:10:00+01:00
scope: infra
category: infra
subcategory: api
domain: [infra, api, mcp]
changelog:
  - 0.3.0 (2026-01-22): Added file operations tools (read_note, write_note, append_to_note, delete_note)
  - 0.2.0 (2026-01-16): Updated tools to reflect AsyncIO implementation
  - 0.1.0 (2026-01-16): Initial documentation of MCP tools
---

## Exposed Tools

The server exposes the following MCP tools to clients. All tools are implemented as `async` functions to ensure non-blocking operation.

### 1. `semantic_search`
- **Type**: Async
- **Purpose**: Retrieve notes semantically matching a query.
- **Inputs**: `query` (str), `n_results` (int), `folder` (opt), `tags` (opt).
- **Output**: List of matches with similarity scores and metadata.
- **Logic**: Embeds query -> Searches VectorStore -> Filters by metadata.

### 2. `reindex_vault`
- **Type**: Async
- **Purpose**: Manually trigger vault indexing.
- **Inputs**: `force` (bool).
- **Output**: Statistics (processed, skipped, duration).
- **Logic**: Delegates to `VaultIndexer.index_vault()`.

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
- **Logic**: Embeds note chunks -> Finds similar chunks in other files -> Aggregates by file.

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
- **Logic**: Reads file → Extracts metadata using utils functions.
- **Use Case**: Cross-codebase access to vault notes.

### 9. `write_note`
- **Type**: Async
- **Purpose**: Create or overwrite a note in the vault.
- **Inputs**: `note_path` (str), `content` (str), `create_dirs` (bool, default: True).
- **Output**: Success status, creation flag, size, chunks indexed.
- **Logic**: Validates path → Creates directories if needed → Writes file → Auto-indexes.
- **Security**: Path validation ensures file stays within vault bounds.

### 10. `append_to_note`
- **Type**: Async
- **Purpose**: Append content to an existing note.
- **Inputs**: `note_path` (str), `content` (str).
- **Output**: Success status, size, chunks indexed.
- **Logic**: Reads existing → Appends content → Writes → Re-indexes.
- **Constraint**: Fails if note doesn't exist (use write_note for new notes).

### 11. `delete_note`
- **Type**: Async
- **Purpose**: Delete a note from filesystem and vector index.
- **Inputs**: `note_path` (str).
- **Output**: Success status and deleted flag.
- **Logic**: Validates file → Deletes from ChromaDB → Deletes from filesystem.
- **Safety**: Warning logged if index deletion fails (but continues with file deletion).

## Transport Modes
- **Stdio**: Default for local CLI use (Claude Desktop).
- **SSE**: Server-Sent Events for remote/persistent deployment (`--sse` flag).