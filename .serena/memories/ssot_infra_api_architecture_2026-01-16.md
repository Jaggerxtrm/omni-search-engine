---
title: SSOT API Architecture (MCP Tools)
version: 0.2.0
updated: 2026-01-16T10:15:00+01:00
scope: infra
category: infra
subcategory: api
domain: [infra, api, mcp]
changelog:
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

## Transport Modes
- **Stdio**: Default for local CLI use (Claude Desktop).
- **SSE**: Server-Sent Events for remote/persistent deployment (`--sse` flag).