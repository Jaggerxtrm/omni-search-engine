from __future__ import annotations

from vaultctl.core.config import load_config
from vaultctl.store.audit import find_duplicates, find_linked, find_orphans
from vaultctl.store.db import connect


def run_audit(mode: str, source: str | None, limit: int) -> list[dict[str, str]]:
    config = load_config()
    conn = connect(config.db_path)
    if mode == "orphans":
        return find_orphans(conn, source, limit)
    if mode == "linked":
        return find_linked(conn, source, limit)
    if mode == "duplicates":
        return find_duplicates(conn, source, limit)
    raise ValueError(f"Unknown audit mode: {mode}")
