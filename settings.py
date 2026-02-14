import os
import yaml
from typing import List, Optional, Dict, Any
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseModel):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    batch_size: int = Field(100, alias="EMBEDDING_BATCH_SIZE")


class ChunkingSettings(BaseModel):
    target_chunk_size: int = Field(1000, alias="TARGET_CHUNK_SIZE")
    max_chunk_size: int = Field(2000, alias="MAX_CHUNK_SIZE")
    min_chunk_size: int = Field(100, alias="MIN_CHUNK_SIZE")


class RerankSettings(BaseModel):
    model: str = Field("ms-marco-TinyBERT-L-2-v2", alias="RERANK_MODEL")
    enabled: bool = Field(True, alias="RERANK_ENABLED")


class WatcherSettings(BaseModel):
    debounce_seconds: float = Field(2.0, alias="WATCHER_DEBOUNCE_SECONDS")
    ai_debounce_seconds: float = Field(5.0, alias="WATCHER_AI_DEBOUNCE_SECONDS")


class SourceConfig(BaseModel):
    id: str
    name: str
    path: Path
    type: str = "general" # code, marketing, documentation, etc.


class Settings(BaseSettings):
    # Legacy/Default Single Vault Support
    obsidian_vault_path: Optional[Path] = Field(None, alias="OBSIDIAN_VAULT_PATH")
    
    # Universal Context Support
    sources: List[SourceConfig] = Field(default_factory=list)
    chromadb_path: Path = Field(Path("chroma_db"), alias="CHROMADB_PATH")

    embedding: EmbeddingSettings = Field(default=None)
    chunking: ChunkingSettings = Field(default=None)
    rerank: RerankSettings = Field(default=None)
    watcher: WatcherSettings = Field(default=None)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode='before')
    @classmethod
    def build_nested_settings(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Construct nested settings from environment variables."""
        # Helper to get value from data (case-insensitive and alias-aware)
        def get_val(key: str, default: Any = None) -> Any:
            return data.get(key.lower(), data.get(key.upper(), default))

        # Build EmbeddingSettings
        if 'embedding' not in data or data['embedding'] is None:
            data['embedding'] = EmbeddingSettings(
                OPENAI_API_KEY=get_val('OPENAI_API_KEY', ''),
                EMBEDDING_MODEL=get_val('EMBEDDING_MODEL', 'text-embedding-3-small'),
                EMBEDDING_BATCH_SIZE=get_val('EMBEDDING_BATCH_SIZE', 100)
            )

        # Build ChunkingSettings
        if 'chunking' not in data or data['chunking'] is None:
            data['chunking'] = ChunkingSettings(
                TARGET_CHUNK_SIZE=get_val('TARGET_CHUNK_SIZE', 1000),
                MAX_CHUNK_SIZE=get_val('MAX_CHUNK_SIZE', 2000),
                MIN_CHUNK_SIZE=get_val('MIN_CHUNK_SIZE', 100)
            )

        # Build RerankSettings
        if 'rerank' not in data or data['rerank'] is None:
            data['rerank'] = RerankSettings(
                RERANK_MODEL=get_val('RERANK_MODEL', 'ms-marco-TinyBERT-L-2-v2'),
                RERANK_ENABLED=get_val('RERANK_ENABLED', True)
            )
            
        # Build WatcherSettings
        if 'watcher' not in data or data['watcher'] is None:
            data['watcher'] = WatcherSettings(
                WATCHER_DEBOUNCE_SECONDS=get_val('WATCHER_DEBOUNCE_SECONDS', 2.0),
                WATCHER_AI_DEBOUNCE_SECONDS=get_val('WATCHER_AI_DEBOUNCE_SECONDS', 5.0)
            )

        return data

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_sources()

    def _load_sources(self):
        """
        Load sources from config.yaml, env vars, and dynamic context.
        Priority:
        1. config.yaml (Static definitions)
        2. Env Vars (Legacy Vault)
        3. Dynamic Context (CWD)
        """
        loaded_ids = set()
        
        # 1. Load from config.yaml if exists
        config_path = Path("config.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                    if data and "sources" in data:
                        for source_data in data["sources"]:
                            source = SourceConfig(**source_data)
                            self.sources.append(source)
                            loaded_ids.add(source.id)
            except Exception as e:
                print(f"Error loading config.yaml: {e}")

        # 2. Legacy Env Var Support (if not already defined in config as 'vault')
        if self.obsidian_vault_path and "vault" not in loaded_ids:
            # If user hasn't defined a 'vault' in config, use the env var
            self.sources.append(SourceConfig(
                id="vault",
                name="Obsidian Vault",
                path=self.obsidian_vault_path,
                type="obsidian"
            ))
            loaded_ids.add("vault")

        # 3. Dynamic Context (Current Project)
        # Avoid adding if CWD is same as Vault
        cwd = Path.cwd().resolve()
        
        # Check if CWD is already covered by an existing source
        is_covered = False
        for source in self.sources:
            if source.path.resolve() == cwd:
                is_covered = True
                break
        
        if not is_covered:
            self.sources.append(SourceConfig(
                id="current_project",
                name="Current Project",
                path=cwd,
                type="code"
            ))


def get_settings() -> Settings:
    return Settings()
