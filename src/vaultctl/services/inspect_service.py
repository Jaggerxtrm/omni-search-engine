from __future__ import annotations

from pathlib import Path

from vaultctl.core.config import load_config
from vaultctl.core.errors import NotFoundError
from vaultctl.store.db import connect


def find(pattern: str, source: str | None, root: str | None, limit: int) -> list[dict[str, str]]:
    config = load_config()
    conn = connect(config.db_path)
    query = "SELECT source_id, rel_path, title FROM documents WHERE rel_path LIKE ?"
    params: list[object] = [f"%{pattern}%"]
    if source:
        query += " AND source_id = ?"
        params.append(source)
    if root:
        query += " AND rel_path LIKE ?"
        params.append(root.rstrip("/") + "%")
    query += " ORDER BY source_id, rel_path LIMIT ?"
    params.append(limit)
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def tree(root: str | None, source: str | None, depth: int | None) -> list[dict[str, str]]:
    config = load_config()
    conn = connect(config.db_path)
    query = "SELECT source_id, rel_path FROM documents"
    params: list[object] = []
    clauses: list[str] = []
    if source:
        clauses.append("source_id = ?")
        params.append(source)
    if root:
        clauses.append("rel_path LIKE ?")
        params.append(root.rstrip("/") + "%")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY source_id, rel_path"
    rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    if depth is None:
        return rows
    filtered: list[dict[str, str]] = []
    for row in rows:
        level = row["rel_path"].count("/") + 1
        if level <= depth:
            filtered.append(row)
    return filtered


def context(target: str) -> dict[str, object]:
    if ":" not in target:
        raise NotFoundError("Target must be source_id:rel/path.md")
    source_id, rel_path = target.split(":", 1)
    config = load_config()
    conn = connect(config.db_path)
    doc = conn.execute(
        "SELECT title, status, tags_text FROM documents WHERE source_id=? AND rel_path=?",
        (source_id, rel_path),
    ).fetchone()
    if not doc:
        raise NotFoundError(f"No indexed document for {target}")
    links = [row[0] for row in conn.execute(
        "SELECT target FROM document_links l JOIN documents d ON d.id=l.document_id WHERE d.source_id=? AND d.rel_path=?",
        (source_id, rel_path),
    ).fetchall()]
    backlinks = [dict(row) for row in conn.execute(
        """
        SELECT d.source_id, d.rel_path, d.title
        FROM document_links l JOIN documents d ON d.id=l.document_id
        WHERE l.target = ?
        ORDER BY d.source_id, d.rel_path
        """,
        (doc["title"],),
    ).fetchall()]
    return {
        "source_id": source_id,
        "rel_path": rel_path,
        "title": doc["title"],
        "status": doc["status"],
        "tags": doc["tags_text"].split() if doc["tags_text"] else [],
        "links": links,
        "backlinks": backlinks,
    }


def status() -> dict[str, object]:
    config = load_config()
    conn = connect(config.db_path)
    db_exists = Path(config.db_path).exists()
    doc_count = int(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]) if db_exists else 0
    return {
        "db_path": str(config.db_path),
        "db_exists": db_exists,
        "documents": doc_count,
        "sources": [source.id for source in config.sources],
    }
