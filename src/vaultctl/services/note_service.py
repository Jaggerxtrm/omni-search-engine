from __future__ import annotations

from pathlib import Path

from vaultctl.core.config import load_config
from vaultctl.core.errors import NotFoundError
from vaultctl.ingest.markdown import WIKILINK_RE
from vaultctl.store.db import connect
from vaultctl.store.indexer import index_source


def _resolve_path(path_arg: str, source_id: str | None) -> tuple[str, Path, Path]:
    config = load_config()
    source = next((item for item in config.sources if item.id == source_id), config.sources[0]) if source_id else config.sources[0]
    path = Path(path_arg)
    abs_path = path if path.is_absolute() else source.root / path
    return source.id, source.root, abs_path


def read_note(path_arg: str, source: str | None = None) -> str:
    _, _, abs_path = _resolve_path(path_arg, source)
    if not abs_path.exists():
        raise NotFoundError(f"Note does not exist: {abs_path}")
    return abs_path.read_text(encoding="utf-8")


def write_note(path_arg: str, content: str, source: str | None = None) -> dict[str, str]:
    source_id, _, abs_path = _resolve_path(path_arg, source)
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    _reindex(source_id)
    return {"source_id": source_id, "path": str(abs_path)}


def append_note(path_arg: str, content: str, source: str | None = None) -> dict[str, str]:
    current = ""
    try:
        current = read_note(path_arg, source)
    except NotFoundError:
        current = ""
    combined = current + ("\n" if current and not current.endswith("\n") else "") + content
    return write_note(path_arg, combined, source)


def delete_note(path_arg: str, source: str | None = None) -> dict[str, str]:
    source_id, _, abs_path = _resolve_path(path_arg, source)
    if abs_path.exists():
        abs_path.unlink()
    _reindex(source_id, full=True)
    return {"source_id": source_id, "path": str(abs_path)}


def extract_links(path_arg: str, source: str | None = None) -> list[str]:
    content = read_note(path_arg, source)
    return sorted({match.group(1).strip() for match in WIKILINK_RE.finditer(content)})


def index_note(path_arg: str, source: str | None = None) -> dict[str, str]:
    source_id, _, _ = _resolve_path(path_arg, source)
    _reindex(source_id)
    return {"indexed": path_arg, "source_id": source_id}


def _reindex(source_id: str, full: bool = False) -> None:
    config = load_config()
    conn = connect(config.db_path)
    source = next(item for item in config.sources if item.id == source_id)
    index_source(conn, source, full=full)
