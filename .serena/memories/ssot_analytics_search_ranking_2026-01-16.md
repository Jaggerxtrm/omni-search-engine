---
title: SSOT Analytics & Search Ranking
version: 0.1.0
updated: 2026-01-16T10:00:00+01:00
scope: analytics
category: analytics
subcategory: search
domain: [analytics, search, ranking]
changelog:
  - 0.1.0 (2026-01-16): Documentation of search logic
---

## Search Algorithm
1.  **Input**: Natural language query.
2.  **Embedding**: Query is embedded using the same model as the index.
3.  **Retrieval**: k-Nearest Neighbors (k-NN) search in ChromaDB (Cosine Similarity).
4.  **Filtering**: Optional pre-filtering by `folder` or `tags` metadata.
5.  **Scoring**:
    *   `distance` returned by ChromaDB.
    *   `similarity = 1 - distance`.

## Link Suggestion Algorithm
1.  **Source**: Target note content.
2.  **Embedding**: Reuses existing embeddings if cached; otherwise generates new ones.
3.  **Query**: Each chunk of the source note queries the vector store.
4.  **Aggregation**:
    *   Matches are grouped by target file.
    *   `exclude_current`: Self-references removed.
5.  **Scoring Strategy**:
    *   Weighted Score = `(max_chunk_similarity * 0.7) + (avg_chunk_similarity * 0.3)`.
    *   Rewards files with highly relevant specific sections while considering overall relevance.
6.  **Presentation**: Returns top `n` files with a specific "reason" (highest matching header context).
