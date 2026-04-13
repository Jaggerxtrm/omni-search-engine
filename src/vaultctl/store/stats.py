from __future__ import annotations

import sqlite3
from typing import Any


def collect_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    source_rows = conn.execute("SELECT id, root, include_glob FROM sources ORDER BY id").fetchall()
    doc_count = int(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
    section_count = int(conn.execute("SELECT COUNT(*) FROM sections").fetchone()[0])
    latest = conn.execute("SELECT MAX(updated_at) FROM documents").fetchone()[0]
    return {
        "documents": doc_count,
        "sections": section_count,
        "last_updated": latest,
        "sources": [dict(row) for row in source_rows],
    }
