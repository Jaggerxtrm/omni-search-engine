---
title: SSOT - Analytics & Tools
version: 1.1.0
updated: 2026-01-24T14:32:00+01:00
scope: analytics
category: analytics
subcategory: tools
domain: [analytics, linking, deduplication, graph]
changelog:
  - 1.1.0 (2026-01-24): Added Orphans, Most Linked, and Duplicate Content tools.
  - 1.0.0 (2026-01-16): Feature implemented (Link Deduplication)
---

## Overview
The Omni Search Engine provides a suite of analytics tools to help users maintain a healthy and interconnected knowledge base.

## Available Tools

### 1. Link Deduplication
Prevents `suggest_links` from recommending notes that are already linked in the source document.
*   **Runtime**: Parses current file content to get existing wikilinks.
*   **Storage**: Maintains `outbound_links` metadata in ChromaDB for graph analysis.

### 2. Orphaned Notes
Identifies notes that are isolated (have zero incoming links).
*   **Tool**: `get_orphaned_notes`
*   **Logic**:
    1.  Get all file paths in vault.
    2.  Collect all `outbound_links` from all note metadata.
    3.  Compute `All Files - Linked Files`.
*   **Use Case**: Finding forgotten or disconnected knowledge.

### 3. Most Linked Notes
Identifies the "pillars" of the vault—notes with the highest number of incoming links.
*   **Tool**: `get_most_linked_notes`
*   **Logic**: Aggregates link counts from the vector store statistics.
*   **Use Case**: Identifying Maps of Content (MOCs) or core concepts.

### 4. Duplicate Content Detection
Finds notes that are semantically identical or very similar.
*   **Tool**: `get_duplicate_content`
*   **Logic**:
    1.  Retrieves all embeddings.
    2.  Computes "centroid" embedding for each file (average of chunk vectors).
    3.  Performs pairwise Cosine Similarity check.
    4.  Returns pairs with similarity > threshold (default 0.95).
*   **Use Case**: merging redundant notes or cleaning up accidental copies.

## Implementation Details

### Metadata Schema
To support these tools, the indexer maintains specific metadata:
- `outbound_links`: Comma-separated list of target note titles.
- `content_hash`: MD5 hash for change detection.
- `file_path`: Relative path for unique identification.

### Performance
- **Duplicate Detection**: Uses `numpy` for efficient vector operations. Complexity is O(N^2) on the number of files, which is acceptable for typical personal vaults (<10k notes).
