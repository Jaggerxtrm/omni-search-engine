from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class ChunkingSettings(BaseSettings):
    target_chunk_size: int = 800
    max_chunk_size: int = 1500
    min_chunk_size: int = 100

class EmbeddingSettings(BaseSettings):
    model: str = "text-embedding-3-small"
    batch_size: int = 100
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")

class SearchSettings(BaseSettings):
    default_n_results: int = 5
    similarity_threshold: float = 0.7

class Settings(BaseSettings):
    # Vault Paths
    obsidian_vault_path: Path = Field(default=Path("/vault"), alias="OBSIDIAN_VAULT_PATH")
    chromadb_path: Path = Field(default=Path("/data/chromadb"), alias="CHROMADB_PATH")
    
    # Sub-configs
    chunking: ChunkingSettings = ChunkingSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    search: SearchSettings = SearchSettings()

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore"
    )

def get_settings() -> Settings:
    return Settings()
