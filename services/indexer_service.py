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
        Index entire vault with incremental updates.

        Args:
            force: If True, reindex all files regardless of changes

        Returns:
            IndexingResult with statistics
        """
        start_time = time.time()
        result = IndexingResult()

        logger.info("Starting vault indexing...")
        logger.info(f"Vault path: {self.vault_path}")
        logger.info(f"Force reindex: {force}")

        # Discover markdown files
        markdown_files = self._discover_markdown_files()
        logger.info(f"Found {len(markdown_files)} markdown files")

        # Index each file
        for i, file_path in enumerate(markdown_files, 1):
            relative_path = get_relative_path(file_path, self.vault_path)
            logger.info(f"[{i}/{len(markdown_files)}] Processing: {relative_path}")

            try:
                # Check if file needs indexing
                if not force:
                    if self._should_skip_file(file_path):
                        logger.debug(f"  ⊘ Skipped (unchanged): {relative_path}")
                        result.notes_skipped += 1
                        continue

                # Index the file
                chunks_count = await self.index_single_file(file_path)
                logger.info(f"  ✓ Indexed {relative_path} ({chunks_count} chunks)")
                result.notes_processed += 1
                result.chunks_created += chunks_count

            except Exception as e:
                error_msg = f"Error indexing {relative_path}: {str(e)}"
                logger.error(f"  ✗ {error_msg}")
                result.errors.append(error_msg)

        print()

        # Cleanup orphaned files
        if not force:
            print("Cleaning up orphaned files...")
            orphans_removed = self._cleanup_orphans(markdown_files)
            print(f"✓ Removed {orphans_removed} orphaned files")
            print()

        result.duration_seconds = time.time() - start_time
        return result

    def _discover_markdown_files(self) -> list[Path]:
        """
        Discover all markdown files in vault.

        Skips hidden directories (.obsidian, .git, etc.)

        Returns:
            List of Path objects for markdown files
        """
        markdown_files = []

        for path in self.vault_path.rglob("*.md"):
            # Skip hidden directories
            if any(part.startswith(".") for part in path.parts):
                continue

            # Skip if not a file
            if not path.is_file():
                continue

            markdown_files.append(path)

        return sorted(markdown_files)

    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Check if file should be skipped (unchanged since last index).

        Args:
            file_path: Absolute path to file

        Returns:
            True if file should be skipped
        """
        # Read current content
        with open(file_path, encoding="utf-8") as f:
            current_content = f.read()

        # Compute current hash
        current_hash = compute_content_hash(current_content)

        # Check stored hash
        relative_path = get_relative_path(file_path, self.vault_path)
        stored_hash = self.vector_store.check_content_hash(relative_path)

        # Skip if hashes match
        return current_hash == stored_hash

    async def index_single_file(self, file_path: Path) -> int:
        """
        Index a single markdown file.

        Args:
            file_path: Absolute path to file

        Returns:
            Number of chunks created
        """
        # Read file content
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Optimize: Check if content changed
        current_hash = compute_content_hash(content)
        relative_path = get_relative_path(file_path, self.vault_path)

        stored_hash = self.vector_store.check_content_hash(relative_path)
        if stored_hash == current_hash:
            logger.debug(f"Skipping unchanged file: {relative_path}")
            return 0

        logger.info(f"Indexing file: {relative_path}")

        # Extract metadata
        note_title = get_note_title(file_path)
        folder = get_folder(file_path, self.vault_path)
        tags = extract_all_tags(content)
        modified_date = file_path.stat().st_mtime

        # Restore content_hash variable for metadata usage
        content_hash = current_hash

        # Chunk the content
        chunks = self.chunker.chunk_markdown(content)

        if not chunks:
            # Empty file, just delete any existing chunks
            logger.warning(f"File is empty or no valid chunks: {relative_path}. Deleting index.")
            self.vector_store.delete_by_file_path(relative_path)
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
                "note_title": chunk.note_title,
                "chunk_index": chunk.chunk_index,
                "header_context": chunk.header_context,
                "folder": chunk.folder,
                "tags": chunk.tags,
                "modified_date": modified_date,
                "content_hash": content_hash,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ]
        ids = [f"{relative_path}::{chunk.chunk_index}" for chunk in chunks]

        # Update: Delete old chunks first to ensure no "ghost" chunks remain
        # if the file was shortened.
        self.vector_store.delete_by_file_path(relative_path)

        # Add new chunks
        self.vector_store.add_chunks(
            embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids
        )

        return len(chunks)

    async def move_file(self, src_path: Path, dest_path: Path) -> bool:
        """
        Handle file move/rename efficiently by reusing embeddings.

        Args:
            src_path: Absolute path to source file (old)
            dest_path: Absolute path to destination file (new)

        Returns:
            True if move was handled (embeddings reused), False if re-indexing was needed.
        """
        rel_src = get_relative_path(src_path, self.vault_path)
        rel_dest = get_relative_path(dest_path, self.vault_path)

        # 1. Fetch existing chunks for source
        old_data = self.vector_store.get_by_file_path(rel_src)

        if not old_data["ids"]:
            # No existing index for source, just index new file normally
            await self.index_single_file(dest_path)
            return False

        # 2. Prepare new data re-using embeddings
        new_embeddings = old_data["embeddings"]
        new_documents = old_data["documents"]

        # Update metadata with new path info
        # We need to re-calculate folder, but other chunks details (index, context) logic
        # relies on content being same.
        # NOTE: If content changed strictly during move, this might be stale, but
        # on_moved usually implies just fs path change.

        new_folder = get_folder(dest_path, self.vault_path)
        new_note_title = get_note_title(dest_path)

        new_metadatas = []
        new_ids = []

        for i, old_meta in enumerate(old_data["metadatas"]):
            # Create copy of metadata
            meta = old_meta.copy()

            # Update path-related fields
            meta["file_path"] = rel_dest
            meta["note_title"] = new_note_title
            meta["folder"] = new_folder

            # Reconstruct ID
            chunk_index = meta.get("chunk_index", i)
            new_id = f"{rel_dest}::{chunk_index}"

            new_metadatas.append(meta)
            new_ids.append(new_id)

        # 3. Add chunk to new path
        # First clean up any pre-existing chunks at DEST (overwrite)
        self.vector_store.delete_by_file_path(rel_dest)

        self.vector_store.add_chunks(
            embeddings=new_embeddings, documents=new_documents, metadatas=new_metadatas, ids=new_ids
        )

        # 4. Delete old chunks
        self.vector_store.delete_by_file_path(rel_src)

        return True

    def _cleanup_orphans(self, current_files: list[Path]) -> int:
        """
        Remove entries for files no longer in vault.

        Args:
            current_files: List of current markdown files in vault

        Returns:
            Number of orphaned files removed
        """
        # Get current file paths (relative)
        current_paths = {get_relative_path(f, self.vault_path) for f in current_files}

        # Get indexed file paths
        indexed_paths = self.vector_store.get_all_file_paths()

        # Find orphans
        orphans = indexed_paths - current_paths

        # Delete orphans
        for orphan_path in orphans:
            self.vector_store.delete_by_file_path(orphan_path)

        return len(orphans)


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
