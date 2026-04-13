from __future__ import annotations

from pathlib import Path


def normalize_rel_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")
