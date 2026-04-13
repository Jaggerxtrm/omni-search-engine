from __future__ import annotations

import sqlite3
from typing import Any

from vaultctl.store.queries import FTS_SEARCH_SQL


def search_documents(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
    source: str | None = None,
    folder: str | None = None,
    tag: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    rows = conn.execute(FTS_SEARCH_SQL, {"query": query, "limit": limit}).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        metadata = conn.execute(
            """
            SELECT d.status, d.tags_text
            FROM documents d
            WHERE d.source_id=? AND d.rel_path=?
            """,
            (row["source_id"], row["rel_path"]),
        ).fetchone()
        if source and row["source_id"] != source:
            continue
        if folder and not str(row["rel_path"]).startswith(folder.rstrip("/") + "/") and str(row["rel_path"]) != folder.rstrip("/"):
            continue
        tags_text = str(metadata["tags_text"] if metadata else "")
        if tag and tag not in tags_text.split():
            continue
        doc_status = str(metadata["status"]) if metadata and metadata["status"] is not None else None
        if status and doc_status != status:
            continue
        results.append(
            {
                "score": float(row["score"]),
                "source_id": row["source_id"],
                "rel_path": row["rel_path"],
                "title": row["title"],
                "snippet": row["snippet"],
                "tags": tags_text.split() if tags_text else [],
                "status": doc_status,
            }
        )
    return results[:limit]
