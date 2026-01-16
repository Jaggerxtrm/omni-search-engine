from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class EmbeddingSettings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    batch_size: int = Field(100, alias="EMBEDDING_BATCH_SIZE")

class ChunkingSettings(BaseSettings):
    target_chunk_size: int = Field(1000, alias="TARGET_CHUNK_SIZE")
    max_chunk_size: int = Field(2000, alias="MAX_CHUNK_SIZE")
    min_chunk_size: int = Field(100, alias="MIN_CHUNK_SIZE")

class Settings(BaseSettings):
    obsidian_vault_path: Path = Field(..., alias="OBSIDIAN_VAULT_PATH")
    chromadb_path: Path = Field(Path("chroma_db"), alias="CHROMADB_PATH")
    
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def get_settings() -> Settings:
    return Settings()
