from __future__ import annotations

from pathlib import Path

from vaultctl.core.models import SourceConfig


def iter_source_paths(source: SourceConfig) -> list[Path]:
    if not source.root.exists():
        return []
    return sorted(path for path in source.root.glob(source.include_glob) if path.is_file())
