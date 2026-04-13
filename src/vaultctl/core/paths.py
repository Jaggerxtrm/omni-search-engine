from __future__ import annotations

from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "vaultctl" / "config.toml"
DB_PATH = Path.home() / ".local" / "share" / "vaultctl" / "index.db"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
