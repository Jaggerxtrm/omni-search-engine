---
title: SSOT - Analytics - Link Deduplication
version: 1.0.0
updated: 2026-01-16T10:30:00+01:00
scope: analytics
category: analytics
subcategory: linking
domain: [analytics, linking, deduplication]
changelog:
  - 1.0.0 (2026-01-16): Feature implemented
---

## Overview
Link deduplication prevents `suggest_links` from recommending notes that are already linked in the source document.

## Implementation Details

### 1. Extraction (`utils.py`)
- **Function**: `extract_wikilinks(content: str) -> List[str]`
- **Logic**: regex `\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]`
- **Output**: List of note titles (e.g., `["Note A", "Note B"]`).

### 2. Storage (`indexer_service.py`)
- **Metadata**: Stored in ChromaDB as `outbound_links` (comma-separated string).
- **Purpose**: Allows future graph analysis without re-parsing content.

### 3. Filtering (`server.py`)
- **Runtime**: `suggest_links` parses the *current* file content to get `existing_links`.
- **Logic**: `if candidate_title in existing_links: continue`.
- **Reasoning**: Uses fresh content (read from disk) rather than metadata to ensure accuracy even if the index is slightly stale.
