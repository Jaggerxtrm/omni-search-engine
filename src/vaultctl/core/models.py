from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceConfig:
    id: str
    root: Path
    include_glob: str


@dataclass(frozen=True)
class AppConfig:
    db_path: Path
    sources: tuple[SourceConfig, ...]


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    rel_path: str
    title: str
    score: float
    snippet: str
    tags: tuple[str, ...]
    status: str | None
