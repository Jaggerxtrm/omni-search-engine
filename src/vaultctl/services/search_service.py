from __future__ import annotations

from vaultctl.core.config import load_config
from vaultctl.store.db import connect
from vaultctl.store.search import search_documents


def run_search(
    query: str,
    limit: int,
    source: str | None = None,
    folder: str | None = None,
    tag: str | None = None,
    status: str | None = None,
) -> list[dict[str, object]]:
    config = load_config()
    conn = connect(config.db_path)
    return search_documents(conn, query, limit, source, folder, tag, status)
