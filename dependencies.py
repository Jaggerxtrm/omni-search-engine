from functools import lru_cache
from settings import get_settings
from repositories.snippet_repository import VectorStore
from services.embedding_service import EmbeddingService
from crawlers.markdown_crawler import MarkdownChunker
from services.indexer_service import VaultIndexer

@lru_cache()
def get_vector_store() -> VectorStore:
    settings = get_settings()
    return VectorStore(
        persist_directory=str(settings.chromadb_path),
        collection_name="obsidian_notes"
    )

@lru_cache()
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(
        api_key=settings.embedding.openai_api_key,
        model=settings.embedding.model,
        batch_size=settings.embedding.batch_size
    )

@lru_cache()
def get_chunker() -> MarkdownChunker:
    settings = get_settings()
    return MarkdownChunker(
        target_chunk_size=settings.chunking.target_chunk_size,
        max_chunk_size=settings.chunking.max_chunk_size,
        min_chunk_size=settings.chunking.min_chunk_size
    )

@lru_cache()
def get_indexer() -> VaultIndexer:
    settings = get_settings()
    return VaultIndexer(
        vault_path=settings.obsidian_vault_path,
        vector_store=get_vector_store(),
        embedding_service=get_embedding_service(),
        chunker=get_chunker()
    )
