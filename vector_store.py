"""
ChromaDB Vector Store Manager

Wrapper for ChromaDB operations: storing embeddings, querying for semantic search,
and managing metadata. Provides methods for incremental updates and orphan cleanup.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import chromadb
from chromadb.config import Settings


class VectorStore:
    """
    Vector store manager using ChromaDB for embedding storage and retrieval.

    Features:
    - Persistent local storage
    - Metadata filtering for advanced queries
    - Content hash tracking for incremental indexing
    - File path-based operations for updates and cleanup
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "obsidian_notes"
    ):
        """
        Initialize vector store with persistent ChromaDB.

        Args:
            persist_directory: Path to ChromaDB storage directory
            collection_name: Name of the ChromaDB collection
        """
        self.persist_directory = Path(persist_directory).expanduser().resolve()
        self.collection_name = collection_name

        # Create directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def add_chunks(
        self,
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add chunks with embeddings to the vector store.

        Args:
            embeddings: List of embedding vectors
            documents: List of chunk content texts
            metadatas: List of metadata dicts for each chunk
            ids: List of unique IDs for each chunk

        Raises:
            ValueError: If input lists have mismatched lengths
        """
        if not (len(embeddings) == len(documents) == len(metadatas) == len(ids)):
            raise ValueError("All input lists must have the same length")

        if embeddings is None or len(embeddings) == 0:
            return  # Nothing to add

        # ChromaDB requires metadata values to be str, int, float, or bool
        # Convert any list fields to strings
        processed_metadatas = []
        for metadata in metadatas:
            processed = {}
            for key, value in metadata.items():
                if isinstance(value, list):
                    # Convert list to comma-separated string
                    processed[key] = ",".join(str(v) for v in value)
                elif value is None:
                    # ChromaDB doesn't accept None values
                    processed[key] = ""
                else:
                    processed[key] = value
            processed_metadatas.append(processed)

        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=processed_metadatas,
            ids=ids
        )

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query vector store for similar chunks.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filters (e.g., {"folder": "1-projects"})

        Returns:
            Dict with keys: 'ids', 'documents', 'metadatas', 'distances'
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

        # Flatten results (query returns list of lists)
        return {
            'ids': results['ids'][0] if results['ids'] else [],
            'documents': results['documents'][0] if results['documents'] else [],
            'metadatas': results['metadatas'][0] if results['metadatas'] else [],
            'distances': results['distances'][0] if results['distances'] else []
        }

    def get_by_file_path(self, file_path: str) -> Dict[str, Any]:
        """
        Retrieve all chunks for a specific file.

        Args:
            file_path: Relative file path in vault

        Returns:
            Dict with keys: 'ids', 'documents', 'metadatas'
        """
        results = self.collection.get(
            where={"file_path": file_path},
            include=["embeddings", "documents", "metadatas"]
        )

        return {
            'ids': results['ids'],
            'documents': results['documents'],
            'metadatas': results['metadatas'],
            'embeddings': results['embeddings']
        }

    def check_content_hash(self, file_path: str) -> Optional[str]:
        """
        Check if file exists in index and return its stored content hash.

        Args:
            file_path: Relative file path in vault

        Returns:
            Content hash string if file exists, None otherwise
        """
        results = self.collection.get(
            where={"file_path": file_path},
            limit=1
        )

        if results['metadatas']:
            return results['metadatas'][0].get('content_hash')
        return None

    def delete_by_file_path(self, file_path: str) -> None:
        """
        Delete all chunks for a specific file.

        Args:
            file_path: Relative file path in vault
        """
        # Get all chunk IDs for this file
        results = self.collection.get(
            where={"file_path": file_path}
        )

        if results['ids']:
            self.collection.delete(ids=results['ids'])

    def get_all_file_paths(self) -> Set[str]:
        """
        Get set of all file paths currently in the index.

        Returns:
            Set of file path strings
        """
        # Get all documents
        results = self.collection.get()

        # Extract unique file paths from metadata
        file_paths = set()
        for metadata in results['metadatas']:
            if 'file_path' in metadata:
                file_paths.add(metadata['file_path'])

        return file_paths

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dict with stats: total_chunks, total_files, collection_name
        """
        # Count total chunks
        all_data = self.collection.get()
        total_chunks = len(all_data['ids'])

        # Count unique files
        file_paths = self.get_all_file_paths()
        total_files = len(file_paths)

        return {
            'total_chunks': total_chunks,
            'total_files': total_files,
            'collection_name': self.collection_name,
            'persist_directory': str(self.persist_directory)
        }

    def reset(self) -> None:
        """
        Delete all data from the collection.

        Warning: This operation cannot be undone!
        """
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )


def create_vector_store(
    persist_directory: str,
    collection_name: str = "obsidian_notes"
) -> VectorStore:
    """
    Convenience function to create a vector store.

    Args:
        persist_directory: Path to ChromaDB storage directory
        collection_name: Name of the collection

    Returns:
        Configured VectorStore instance
    """
    return VectorStore(
        persist_directory=persist_directory,
        collection_name=collection_name
    )
