from __future__ import annotations

import json
from typing import Any


def emit(data: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if isinstance(data, list):
        for row in data:
            print(_format_row(row))
        return
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
        return
    print(data)


def _format_row(row: object) -> str:
    if not isinstance(row, dict):
        return str(row)
    title = row.get("title", "")
    path = row.get("rel_path", "")
    source = row.get("source_id", "")
    score = row.get("score")
    prefix = f"[{score:.4f}] " if isinstance(score, float) else ""
    return f"{prefix}{source}:{path} {title}".strip()
