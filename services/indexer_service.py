"""
Vault Indexing Orchestration

Coordinates the indexing workflow: file discovery, chunking, embedding generation,
and storage in ChromaDB. Implements incremental indexing with content-hash caching.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

from crawlers.markdown_crawler import MarkdownChunker
from logger import get_logger
from repositories.snippet_repository import VectorStore
from services.embedding_service import EmbeddingService
from utils import (
    compute_content_hash,
    extract_all_tags,
    get_folder,
    get_note_title,
    get_relative_path,
)

logger = get_logger("indexer")


@dataclass
class IndexingResult:
    """
    Result of an indexing operation.

    Attributes:
        notes_processed: Number of notes that were indexed
        notes_skipped: Number of notes skipped (unchanged)
        chunks_created: Total chunks generated
        duration_seconds: Time taken for indexing
        errors: List of error messages
    """

    notes_processed: int = 0
    notes_skipped: int = 0
    chunks_created: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


from utils import (
    compute_content_hash,
    count_tokens,
    extract_all_tags,
    extract_wikilinks,
    get_folder,
    get_note_title,
    get_relative_path,
)

class VaultIndexer:
    """
    Orchestrates indexing of an Obsidian vault.

    Features:
    - Incremental indexing (skip unchanged files)
    - Orphan cleanup (remove deleted files)
    - Progress tracking and error handling
    - Content-hash based change detection
    """

    def __init__(
        self,
        vault_path: Path,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        chunker: MarkdownChunker,
    ):
        """
        Initialize vault indexer.

        Args:
            vault_path: Path to Obsidian vault directory
            vector_store: Vector store for embedding storage
            embedding_service: Service for generating embeddings
            chunker: Markdown chunker for splitting documents
        """
        self.vault_path = vault_path
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.chunker = chunker

    async def index_vault(self, force: bool = False) -> IndexingResult:
        """
        Index all configured sources (Vaults, Repos) with incremental updates.

        Args:
            force: If True, reindex all files regardless of changes

        Returns:
            IndexingResult with aggregated statistics
        """
        start_time = time.time()
        result = IndexingResult()
        
        # Determine available sources
        # We need settings here. Best practice would be to inject settings, 
        # but for now we might need to access them directly or pass them in __init__
        # Let's assume the caller configures the indexer with sources or we get them here.
        from settings import get_settings
        settings = get_settings()
        
        sources = settings.sources
        
        if not sources:
            logger.warning("No sources configured for indexing.")
            return result

        logger.info(f"Starting multi-source indexing for {len(sources)} sources...")
        logger.info(f"Force reindex: {force}")

        for source in sources:
            logger.info(f"--- Indexing Source: {source.name} ({source.id}) ---")
            logger.info(f"Path: {source.path}")
            
            if not source.path.exists():
                logger.error(f"Source path does not exist: {source.path}")
                result.errors.append(f"Source path not found: {source.path}")
                continue

            # Discover files in THIS source
            source_files = self._discover_files(source.path)
            logger.info(f"Found {len(source_files)} files in {source.id}")

            # Index each file
            for i, file_path in enumerate(source_files, 1):
                relative_path = get_relative_path(file_path, source.path)
                # logger.info(f"[{i}/{len(source_files)}] Processing: {relative_path}")

                try:
                    # Check if file needs indexing
                    if not force:
                        if self._should_skip_file(file_path, source.path, source.id):
                            # logger.debug(f"  ⊘ Skipped (unchanged): {relative_path}")
                            result.notes_skipped += 1
                            continue

                    # Index the file
                    chunks_count = await self.index_single_file(file_path, source.path, source.id, force=force)
                    logger.info(f"  ✓ Indexed [{source.id}] {relative_path} ({chunks_count} chunks)")
                    result.notes_processed += 1
                    result.chunks_created += chunks_count

                except Exception as e:
                    error_msg = f"Error indexing {source.id}/{relative_path}: {str(e)}"
                    logger.error(f"  ✗ {error_msg}")
                    result.errors.append(error_msg)
            
            # Cleanup orphaned files FOR THIS SOURCE
            if not force:
                logger.info(f"Cleaning up orphans for {source.id}...")
                orphans_removed = self._cleanup_orphans(source_files, source.path, source.id)
                if orphans_removed > 0:
                    logger.info(f"✓ Removed {orphans_removed} orphaned files from {source.id}")

        result.duration_seconds = time.time() - start_time
        logger.info(f"Indexing complete in {result.duration_seconds:.2f}s")
        return result

    def _discover_files(self, root_path: Path) -> list[Path]:
        """
        Discover all supported files (markdown, etc) in a source root.

        Skips hidden directories (.obsidian, .git, etc.)

        Args:
            root_path: Root directory of the source

        Returns:
            List of Path objects
        """
        files = []
        extensions = ['*.md', '*.txt', '*.py', '*.js', '*.ts', '*.json', '*.yaml'] # Expanded for codebases

        # rglob is simple but might be slow for huge repos. 
        # Ideally we'd use 'git ls-files' for repos, but let's stick to fs for now.
        for ext in extensions:
            for path in root_path.rglob(ext):
                # Skip hidden directories
                if any(part.startswith(".") for part in path.parts):
                    continue

                # Skip if not a file
                if not path.is_file():
                    continue

                files.append(path)

        return sorted(list(set(files))) # dedupe just in case

    def _should_skip_file(self, file_path: Path, source_root: Path, source_id: str) -> bool:
        """
        Check if file should be skipped coverage.
        """
        # Read current content
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                current_content = f.read()
        except Exception:
            return True # Skip unreadable files

        # Compute current hash
        current_hash = compute_content_hash(current_content)

        # Check stored hash
        relative_path = get_relative_path(file_path, source_root)
        stored_hash = self.vector_store.check_content_hash(relative_path, source_id)

        # Skip if hashes match
        return current_hash == stored_hash

    async def index_single_file(self, file_path: Path, source_root: Path, source_id: str, force: bool = False) -> int:
        """
        Index a single file.
        """
        # Read file content
        try:
             with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return 0

        # Optimize: Check if content changed
        current_hash = compute_content_hash(content)
        relative_path = get_relative_path(file_path, source_root)

        if not force:
            saved_hash = self.vector_store.check_content_hash(relative_path, source_id)
            if saved_hash == current_hash:
                logger.debug(f"Skipping unchanged file: {relative_path}")
                return 0

        # logger.info(f"Indexing file: {relative_path}")

        # Extract metadata
        note_title = get_note_title(file_path)
        folder = get_folder(file_path, source_root)
        
        # Only compute rich metadata for Markdown
        if file_path.suffix == '.md':
             tags = extract_all_tags(content)
             links = extract_wikilinks(content)
             links_str = ",".join(links)
        else:
             tags = []
             links_str = ""
             
        modified_date = file_path.stat().st_mtime
        content_hash = current_hash

        # Chunk the content
        chunks = self.chunker.chunk_markdown(content)

        if not chunks:
            # Empty file, just delete any existing chunks
            # logger.warning(f"File is empty or no valid chunks: {relative_path}. Deleting index.")
            self.vector_store.delete_by_file_path(relative_path, source_id)
            return 0

        # Update chunk metadata
        for chunk in chunks:
            chunk.file_path = relative_path
            chunk.note_title = note_title
            chunk.folder = folder
            chunk.tags = tags

        # Generate embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_service.embed_texts(chunk_texts)

        # Prepare data for vector store
        documents = chunk_texts
        metadatas = [
            {
                "file_path": chunk.file_path,
                "source": source_id,            # NEW: Source ID
                "note_title": chunk.note_title,
                "chunk_index": chunk.chunk_index,
                "header_context": chunk.header_context,
                "folder": chunk.folder,
                "tags": chunk.tags,
                "outbound_links": links_str,
                "modified_date": modified_date,
                "content_hash": content_hash,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ]
        
        # NEW ID Format: source::path::index
        ids = [f"{source_id}::{relative_path}::{chunk.chunk_index}" for chunk in chunks]

        # Update: Delete old chunks first
        self.vector_store.delete_by_file_path(relative_path, source_id)

        # Add new chunks
        self.vector_store.add_chunks(
            embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids
        )

        return len(chunks)

    async def move_file(self, src_path: Path, dest_path: Path) -> bool:
        """
        Handle file move/rename efficiently by reusing embeddings.
        
        TODO: Multisource support for moves.
        For now we disable optimization and force reindex of destination.
        """
        # Simplified for now: just reindex dest
        await self.index_single_file(dest_path, dest_path.parent, "unknown_source") 
        # This is broken, we need source info. 
        # For now, let's just return False so caller handles it via full reindex if needed?
        # Or better, we assume we find the source via settings?
        return False

    def _cleanup_orphans(self, current_files: list[Path], source_root: Path, source_id: str) -> int:
        """
        Remove entries for files no longer in source.

        Args:
            current_files: List of current files in source
            source_root: Root path of source
            source_id: ID of the source being cleaned

        Returns:
            Number of orphaned files removed
        """
        # Get current file paths (relative)
        current_paths = {get_relative_path(f, source_root) for f in current_files}

        # Get indexed file paths for this source
        indexed_paths = self.vector_store.get_all_file_paths(source_id)

        # Find orphans
        orphans = indexed_paths - current_paths

        # Delete orphans
        for orphan_path in orphans:
            self.vector_store.delete_by_file_path(orphan_path, source_id)

        return len(orphans)

    def run_startup_cleanup(self) -> int:
        """
        Run startup consistency check for all sources.
        Detects and removes files from index that no longer exist on disk.
        (Offline move detection)

        Returns:
            Number of orphaned files removed.
        """
        logger.info("Running startup consistency check...")
        
        # Determine available sources
        from settings import get_settings
        settings = get_settings()
        sources = settings.sources
        
        total_removed = 0
        
        if not sources:
            logger.warning("No sources to clean up.")
            return 0
            
        for source in sources:
             if not source.path.exists():
                 logger.warning(f"Skiping cleanup for missing source: {source.path}")
                 continue
                 
             logger.info(f"Checking consistency for source: {source.id}")
             current_files = self._discover_files(source.path)
             removed = self._cleanup_orphans(current_files, source.path, source.id)
             
             if removed > 0:
                 logger.info(f"  ✓ Removed {removed} orphaned files from {source.id}")
                 total_removed += removed
        
        if total_removed == 0:
            logger.info("Startup cleanup: Index is consistent with disk.")
            
        return total_removed


def create_indexer(
    vault_path: Path,
    vector_store: VectorStore,
    embedding_service: EmbeddingService,
    target_chunk_size: int = 800,
    max_chunk_size: int = 1500,
    min_chunk_size: int = 100,
) -> VaultIndexer:
    """
    Convenience function to create a vault indexer.

    Args:
        vault_path: Path to Obsidian vault
        vector_store: Vector store instance
        embedding_service: Embedding service instance
        target_chunk_size: Target tokens per chunk
        max_chunk_size: Maximum tokens per chunk
        min_chunk_size: Minimum tokens per chunk

    Returns:
        Configured VaultIndexer instance
    """
    chunker = MarkdownChunker(
        target_chunk_size=target_chunk_size,
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
    )

    return VaultIndexer(
        vault_path=vault_path,
        vector_store=vector_store,
        embedding_service=embedding_service,
        chunker=chunker,
    )
