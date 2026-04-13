from __future__ import annotations

from vaultctl.core.config import load_config
from vaultctl.store.db import connect
from vaultctl.store.indexer import index_source


def index_sources(source: str | None = None, full: bool = False) -> dict[str, int]:
    config = load_config()
    conn = connect(config.db_path)

    counters: dict[str, int] = {}
    for item in config.sources:
        if source and item.id != source:
            continue
        counters[item.id] = index_source(conn, item, full=full)
    return counters
