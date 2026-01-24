---
title: SSOT Data Ingestion & Indexing
version: 0.3.0
updated: 2026-01-24T14:45:00+01:00
scope: data
category: data
subcategory: ingestion
domain: [data, indexing, crawling]
changelog:
  - 0.3.0 (2026-01-24): Added Startup Cleanup (Offline Move Detection)
  - 0.2.0 (2026-01-24): Updated Watcher logic for file moves/deletions
  - 0.1.0 (2026-01-16): Initial documentation of indexing pipeline
---

## Pipeline Overview

1.  **Discovery**: `VaultIndexer` scans the vault path for `.md` files.
2.  **Change Detection**: Calculates MD5 hash of file content.
    *   Compares with stored hash in `VectorStore`.
    *   Skips if match (Incremental Indexing).
3.  **Parsing & Chunking**:
    *   `Chunker` (implied service) splits markdown.
    *   Preserves header hierarchy context.
    *   Extracts frontmatter and inline tags.
4.  **Embedding**:
    *   Batches chunks.
    *   Sends to OpenAI API (`text-embedding-3-small`).
5.  **Storage**:
    *   Upserts vectors + metadata + content hash to ChromaDB.
    *   Removes stale chunks for updated files.

## Auto-Indexing (Watch Mode)
- **Component**: `VaultWatcher` (Watchdog observer).
- **Events**:
    *   `on_modified`: Debounced trigger for re-indexing single file.
    *   `on_created`: Indexes new file.
    *   `on_deleted`: Removes file chunks from VectorStore.
    *   `on_moved`: Explicit consistency check: removes source file chunks from VectorStore and indexes new file path.
- **Optimization**: Uses event coalescing to prevent rapid-fire API calls during editing.

## Startup Cleanup (Offline Move Detection)
Ensures index consistency when files are modified while the server is offline.
*   **Trigger**: Server startup (`lifespan`).
*   **Action**: Scans current file system and removes any index entries for files that no longer exist (orphans).
*   **Benefit**: Self-healing index, prevents "ghost notes".

## Metadata Schema
Stored with each chunk in ChromaDB:
- `file_path`: Relative path (e.g., "folder/note.md").
- `note_title`: Filename without extension.
- `header_context`: Hierarchy (e.g., "# Title / ## Section").
- `chunk_index`: Sequence number.
- `content_hash`: MD5 of source file.
- `tags`: Comma-separated string.
- `folder`: Parent directory.
