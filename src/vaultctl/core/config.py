from __future__ import annotations

import tomllib
from pathlib import Path

from vaultctl.core.errors import ConfigError
from vaultctl.core.models import AppConfig, SourceConfig
from vaultctl.core.paths import CONFIG_PATH, DB_PATH

DEFAULT_SOURCES = (
    SourceConfig(id="vault", root=Path("/home/dawid/second-mind"), include_glob="**/*.md"),
    SourceConfig(
        id="transcripts",
        root=Path("/home/dawid/dev/transcriptoz/transcripts"),
        include_glob="*.analysis.md",
    ),
)


def load_config(config_path: Path = CONFIG_PATH) -> AppConfig:
    if not config_path.exists():
        return AppConfig(db_path=DB_PATH, sources=DEFAULT_SOURCES)

    with config_path.open("rb") as fh:
        data = tomllib.load(fh)

    db_path = Path(data.get("db_path", str(DB_PATH))).expanduser()
    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ConfigError(f"Expected non-empty [[sources]] in {config_path}")

    sources: list[SourceConfig] = []
    for raw_source in raw_sources:
        source_id = raw_source.get("id")
        root = raw_source.get("root")
        include_glob = raw_source.get("include_glob", "**/*.md")
        if not isinstance(source_id, str) or not isinstance(root, str):
            raise ConfigError(f"Invalid source entry in {config_path}: {raw_source}")
        sources.append(SourceConfig(id=source_id, root=Path(root).expanduser(), include_glob=include_glob))

    return AppConfig(db_path=db_path, sources=tuple(sources))
