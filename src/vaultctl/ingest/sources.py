from __future__ import annotations

from pathlib import Path

from vaultctl.core.models import SourceConfig


def iter_source_paths(source: SourceConfig) -> list[Path]:
    if not source.root.exists():
        return []
    excluded: set[Path] = set()
    if source.exclude_glob:
        excluded = set(source.root.glob(source.exclude_glob))
    return sorted(
        path for path in source.root.glob(source.include_glob)
        if path.is_file() and path not in excluded and not any(p in excluded for p in path.parents)
    )
