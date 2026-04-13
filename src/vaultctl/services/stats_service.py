from __future__ import annotations

from vaultctl.core.config import load_config
from vaultctl.store.db import connect
from vaultctl.store.stats import collect_stats


def stats() -> dict[str, object]:
    config = load_config()
    conn = connect(config.db_path)
    return collect_stats(conn)
