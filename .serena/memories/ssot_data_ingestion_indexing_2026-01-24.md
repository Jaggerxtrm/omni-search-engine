---
title: SSOT Data Ingestion & Indexing
version: 0.4.0
updated: 2026-01-24T22:55:00+01:00
scope: data
category: data
subcategory: ingestion
domain: [data, indexing, crawling]
changelog:
  - 0.4.0 (2026-01-24): Added Multi-Source Support and Reranking details.
  - 0.3.0 (2026-01-24): Added Startup Cleanup (Offline Move Detection)
  - 0.2.0 (2026-01-24): Updated Watcher logic for file moves/deletions
  - 0.1.0 (2026-01-16): Initial documentation of indexing pipeline
---

## Pipeline Overview

1.  **Discovery**: 
    *   Iterates over all configured `sources` (e.g., Vault, Current Project).
    *   Scans each source path for supported files (`.md` default, extensible).
2.  **Change Detection**: Calculates MD5 hash of file content.
    *   Compares with stored hash in `VectorStore`.
    *   Skips if match (Incremental Indexing).
3.  **Parsing & Chunking**:
    *   `Chunker` service splits content.
    *   Preserves header hierarchy context.
    *   Extracts frontmatter and inline tags.
4.  **Embedding**:
    *   Batches chunks.
    *   Sends to OpenAI API (`text-embedding-3-small`).
5.  **Storage**:
    *   Upserts vectors + metadata + content hash to ChromaDB.
    *   **ID Schema**: `source::relative_path::chunk_index` (prevents collisions across sources).
    *   Removes stale chunks for updated files.

## Auto-Indexing (Watch Mode)
- **Component**: `VaultWatcher` (Watchdog observer).
- **Multi-Source**: Watches all valid source paths concurrently.
- **Events**:
    *   `on_modified`: Debounced trigger for re-indexing single file.
    *   `on_created`: Indexes new file.
    *   `on_deleted`: Removes file chunks from VectorStore using source-aware paths.
    *   `on_moved`: Explicit consistency check: removes source file chunks and indexes new file path.
- **Optimization**: Uses event coalescing to prevent rapid-fire API calls.

## Startup Cleanup (Offline Move Detection)
Ensures index consistency when files are modified while the server is offline.
*   **Trigger**: Server startup (`lifespan`).
*   **Action**: Iterates all sources, scans file system, and removes index entries for files that no longer exist (orphans).
*   **Benefit**: Self-healing index, prevents "ghost notes".

## Metadata Schema
Stored with each chunk in ChromaDB:
- `source`: Source ID (e.g., "vault", "current_project").
- `file_path`: Relative path within source (e.g., "folder/note.md").
- `note_title`: Filename without extension.
- `header_context`: Hierarchy (e.g., "# Title / ## Section").
- `chunk_index`: Sequence number.
- `content_hash`: MD5 of source file.
- `tags`: Comma-separated string.
- `folder`: Parent directory.
