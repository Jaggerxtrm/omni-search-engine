---
title: Reference - Database Query Patterns
version: 0.1.0
updated: 2026-01-16T10:00:00+01:00
scope: reference
category: reference
subcategory: database
domain: [database, chroma, query]
changelog:
  - 0.1.0 (2026-01-16): Captured existing query patterns
---

## ChromaDB Patterns

### 1. Vector Search
```python
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=k,
    where=filter_dict,  # e.g., {"folder": "projects"}
    where_document=None # Optional text filter
)
```

### 2. ID-Based Retrieval
Used for deduplication or fetching specific chunks.
```python
results = collection.get(
    ids=chunk_ids,
    include=["embeddings", "metadatas", "documents"]
)
```

### 3. Metadata Filtering (`where` clause)
- **Exact Match**: `{"folder": "1-projects"}`
- **List Containment**: Chroma stores tags as strings ("tag1,tag2"), so regex or client-side filtering often needed for robust tag search, though simple `{"tags": "target_tag"}` works for exact string matches.
- **Complex Logic**: `$and`, `$or` supported in newer Chroma versions.

### 4. Delete by Path
Standard pattern for updates/deletes.
```python
collection.delete(
    where={"file_path": relative_path}
)
```
