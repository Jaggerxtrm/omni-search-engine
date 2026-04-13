from __future__ import annotations

import sqlite3
from pathlib import Path

from vaultctl.core.models import SourceConfig
from vaultctl.ingest.markdown import parse_markdown
from vaultctl.ingest.normalizers import normalize_rel_path
from vaultctl.ingest.sources import iter_source_paths
from vaultctl.ingest.transcripts import parse_transcript


def upsert_source(conn: sqlite3.Connection, source: SourceConfig) -> None:
    conn.execute(
        """
        INSERT INTO sources(id, root, include_glob)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET root=excluded.root, include_glob=excluded.include_glob, updated_at=CURRENT_TIMESTAMP
        """,
        (source.id, str(source.root), source.include_glob),
    )


def index_source(conn: sqlite3.Connection, source: SourceConfig, full: bool = False) -> int:
    upsert_source(conn, source)
    changed = 0
    seen_paths: set[str] = set()

    for path in iter_source_paths(source):
        rel_path = normalize_rel_path(path, source.root)
        seen_paths.add(rel_path)
        mtime = path.stat().st_mtime
        row = conn.execute(
            "SELECT id, mtime FROM documents WHERE source_id = ? AND rel_path = ?",
            (source.id, rel_path),
        ).fetchone()
        if row and not full and float(row["mtime"]) >= mtime:
            continue

        content = path.read_text(encoding="utf-8", errors="replace")
        parser = parse_transcript if source.id == "transcripts" else parse_markdown
        parsed = parser(content, path.stem)
        heading_text = " / ".join(parsed.heading_paths)
        tags_text = " ".join(parsed.tags)

        if row:
            document_id = int(row["id"])
            conn.execute(
                """
                UPDATE documents SET abs_path=?, title=?, status=?, body=?, heading_path=?, tags_text=?, mtime=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (str(path), parsed.title, parsed.status, parsed.body, heading_text, tags_text, mtime, document_id),
            )
            conn.execute("DELETE FROM document_tags WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM document_links WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM sections_fts WHERE source_id=? AND rel_path=?", (source.id, rel_path))
        else:
            cursor = conn.execute(
                """
                INSERT INTO documents(source_id, rel_path, abs_path, title, status, body, heading_path, tags_text, mtime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source.id, rel_path, str(path), parsed.title, parsed.status, parsed.body, heading_text, tags_text, mtime),
            )
            document_id = int(cursor.lastrowid)

        for tag in parsed.tags:
            conn.execute("INSERT OR IGNORE INTO document_tags(document_id, tag) VALUES (?, ?)", (document_id, tag))
        for link in parsed.links:
            conn.execute("INSERT OR IGNORE INTO document_links(document_id, target) VALUES (?, ?)", (document_id, link))

        conn.execute(
            "INSERT INTO sections(document_id, heading_path, body) VALUES (?, ?, ?)",
            (document_id, heading_text, parsed.body),
        )
        conn.execute(
            "INSERT INTO sections_fts(title, heading_path, tags_text, body, source_id, rel_path) VALUES (?, ?, ?, ?, ?, ?)",
            (parsed.title, heading_text, tags_text, parsed.body, source.id, rel_path),
        )
        changed += 1

    if full:
        missing = conn.execute(
            "SELECT rel_path FROM documents WHERE source_id=?", (source.id,)
        ).fetchall()
        for row in missing:
            rel_path = str(row["rel_path"])
            if rel_path in seen_paths:
                continue
            conn.execute("DELETE FROM sections_fts WHERE source_id=? AND rel_path=?", (source.id, rel_path))
            conn.execute("DELETE FROM documents WHERE source_id=? AND rel_path=?", (source.id, rel_path))

    conn.commit()
    return changed
