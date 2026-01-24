import os
import yaml
from typing import List, Optional
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    batch_size: int = Field(100, alias="EMBEDDING_BATCH_SIZE")


class ChunkingSettings(BaseSettings):
    target_chunk_size: int = Field(1000, alias="TARGET_CHUNK_SIZE")
    max_chunk_size: int = Field(2000, alias="MAX_CHUNK_SIZE")
    min_chunk_size: int = Field(100, alias="MIN_CHUNK_SIZE")


class RerankSettings(BaseSettings):
    model: str = Field("ms-marco-TinyBERT-L-2-v2", alias="RERANK_MODEL")
    enabled: bool = Field(True, alias="RERANK_ENABLED")


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

    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    rerank: RerankSettings = Field(default_factory=RerankSettings)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
