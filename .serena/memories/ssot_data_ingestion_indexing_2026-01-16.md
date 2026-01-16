---
title: SSOT Data Ingestion & Indexing
version: 0.1.0
updated: 2026-01-16T10:00:00+01:00
scope: data
category: data
subcategory: ingestion
domain: [data, indexing, crawling]
changelog:
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
    *   `on_moved`: Updates paths in VectorStore (delete old -> index new).
- **Optimization**: Uses event coalescing to prevent rapid-fire API calls during editing.

## Metadata Schema
Stored with each chunk in ChromaDB:
- `file_path`: Relative path (e.g., "folder/note.md").
- `note_title`: Filename without extension.
- `header_context`: Hierarchy (e.g., "# Title / ## Section").
- `chunk_index`: Sequence number.
- `content_hash`: MD5 of source file.
- `tags`: Comma-separated string.
- `folder`: Parent directory.
