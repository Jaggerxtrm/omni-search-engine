---
title: SSOT Analytics & Search Ranking
version: 0.2.0
updated: 2026-01-24T22:55:00+01:00
scope: analytics
category: analytics
subcategory: search
domain: [analytics, search, ranking]
changelog:
  - 0.2.0 (2026-01-24): Added Reranking and new Analytics Tools details.
  - 0.1.0 (2026-01-16): Documentation of search logic
---

## Search Algorithm
1.  **Input**: Natural language query.
2.  **Embedding**: Query is embedded using `text-embedding-3-small`.
3.  **Retrieval**: k-Nearest Neighbors (k-NN) search in ChromaDB.
    *   **Fetch Factor**: Retrieves `5 * n_results` candidates if reranking is enabled.
    *   **Filters**: Applies `folder`, `tags`, or `source` filters pre-query.
4.  **Reranking (FlashRank)**:
    *   Model: `ms-marco-TinyBERT-L-2-v2` (Local Cross-Encoder).
    *   Process: Rescores all candidates based on direct query-document interaction.
    *   Output: Sorts by rerank score and slices top `n_results`.
5.  **Scoring**: Final result uses reranker score (or falling back to cosine similarity if disabled).

## Link Suggestion Algorithm
1.  **Source**: Target note content.
2.  **Embedding**: Reuse/Generate embeddings.
3.  **Deduplication**: Filters out notes that are *already linked* in the source document to prevent redundancy.
4.  **Aggregation**: Groups chunk matches by file.
5.  **Scoring**: Weighted score of max and avg chunk similarity.

## Analytics Tools
1.  **Orphan Detection** (`get_orphaned_notes`):
    *   Scans entire vault to build a link graph.
    *   Identifies nodes with `in_degree = 0`.
2.  **Core Concepts** (`get_most_linked_notes`):
    *   Uses link graph to finding notes with highest `in_degree`.
3.  **Duplicate Detection** (`get_duplicate_content`):
    *   Uses vector similarity on *all* chunk pairs (O(N^2) complexity, optimized with thresholds) to find near-exact semantic matches.
