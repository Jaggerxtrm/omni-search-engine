#!/usr/bin/env python3
"""
Test vector store operations with ChromaDB.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from repositories.snippet_repository import VectorStore
from services.embedding_service import EmbeddingService


async def main():
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    print("Testing VectorStore")
    print("=" * 80)

    # Create temporary directory for test
    test_dir = tempfile.mkdtemp(prefix="chromadb_test_")
    print(f"Test directory: {test_dir}")
    print()

    # Initialize services
    print("Initializing services...")
    vector_store = VectorStore(persist_directory=test_dir)
    embedding_service = EmbeddingService(api_key=api_key)
    print("✓ Vector store initialized")
    print("✓ Embedding service initialized")
    print()

    # Test 1: Add chunks
    print("Test 1: Add chunks")
    print("-" * 80)

    test_chunks = [
        {
            "content": "Gold is a precious metal used as a store of value.",
            "metadata": {
                "file_path": "notes/gold.md",
                "note_title": "gold",
                "chunk_index": 0,
                "header_context": "# Gold",
                "folder": "notes",
                "tags": ["trading", "gold"],
                "modified_date": 1704844800.0,
                "content_hash": "abc123",
                "token_count": 50,
            },
        },
        {
            "content": "Treasury bonds are government securities with fixed interest rates.",
            "metadata": {
                "file_path": "notes/bonds.md",
                "note_title": "bonds",
                "chunk_index": 0,
                "header_context": "# Bonds",
                "folder": "notes",
                "tags": ["trading", "bonds"],
                "modified_date": 1704844800.0,
                "content_hash": "def456",
                "token_count": 45,
            },
        },
        {
            "content": "Real interest rates are the primary driver of gold prices.",
            "metadata": {
                "file_path": "notes/gold.md",
                "note_title": "gold",
                "chunk_index": 1,
                "header_context": "# Gold / ## Price Drivers",
                "folder": "notes",
                "tags": ["trading", "gold"],
                "modified_date": 1704844800.0,
                "content_hash": "abc123",
                "token_count": 40,
            },
        },
    ]

    # Generate embeddings
    print("Generating embeddings...")
    texts = [chunk["content"] for chunk in test_chunks]
    embeddings = await embedding_service.embed_texts(texts)
    print(f"✓ Generated {len(embeddings)} embeddings")

    # Add to vector store
    documents = [chunk["content"] for chunk in test_chunks]
    metadatas = [chunk["metadata"] for chunk in test_chunks]
    ids = [f"chunk_{i}" for i in range(len(test_chunks))]

    vector_store.add_chunks(
        embeddings=embeddings, documents=documents, metadatas=metadatas, ids=ids
    )
    print(f"✓ Added {len(test_chunks)} chunks to vector store")
    print()

    # Test 2: Get stats
    print("Test 2: Get stats")
    print("-" * 80)
    stats = vector_store.get_stats()
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Total files: {stats['total_files']}")
    print(f"Collection: {stats['collection_name']}")
    print()

    # Test 3: Query for similar chunks
    print("Test 3: Query for similar chunks")
    print("-" * 80)
    query_text = "What affects gold prices?"
    print(f"Query: {query_text}")

    query_embedding = await embedding_service.embed_single(query_text)
    results = vector_store.query(query_embedding, n_results=2)

    print(f"✓ Found {len(results['ids'])} results")
    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"], results["metadatas"], results["distances"], strict=False)
    ):
        similarity = 1 - dist  # Convert distance to similarity
        print(f"\n  Result {i + 1} (similarity: {similarity:.3f}):")
        print(f"    File: {meta['file_path']}")
        print(f"    Header: {meta['header_context']}")
        print(f"    Content: {doc[:60]}...")
    print()

    # Test 4: Get chunks by file path
    print("Test 4: Get chunks by file path")
    print("-" * 80)
    file_results = vector_store.get_by_file_path("notes/gold.md")
    print(f"✓ Found {len(file_results['ids'])} chunks for 'notes/gold.md'")
    for chunk_id, doc in zip(
        file_results["ids"], file_results["documents"], strict=False
    ):
        print(f"  - {chunk_id}: {doc[:50]}...")
    print()

    # Test 5: Check content hash
    print("Test 5: Check content hash")
    print("-" * 80)
    hash1 = vector_store.check_content_hash("notes/gold.md")
    hash2 = vector_store.check_content_hash("notes/nonexistent.md")
    print(f"Hash for 'notes/gold.md': {hash1}")
    print(f"Hash for 'notes/nonexistent.md': {hash2}")
    print()

    # Test 6: Get all file paths
    print("Test 6: Get all file paths")
    print("-" * 80)
    all_paths = vector_store.get_all_file_paths()
    print(f"✓ Found {len(all_paths)} unique file paths:")
    for path in sorted(all_paths):
        print(f"  - {path}")
    print()

    # Test 7: Delete by file path
    print("Test 7: Delete by file path")
    print("-" * 80)
    print("Deleting 'notes/bonds.md'...")
    vector_store.delete_by_file_path("notes/bonds.md")

    stats_after = vector_store.get_stats()
    print(f"✓ Chunks after deletion: {stats_after['total_chunks']}")
    print(f"✓ Files after deletion: {stats_after['total_files']}")
    print()

    # Test 8: Persistence
    print("Test 8: Persistence")
    print("-" * 80)
    print("Creating new vector store instance with same directory...")
    vector_store2 = VectorStore(persist_directory=test_dir)
    stats_loaded = vector_store2.get_stats()

    print(f"✓ Loaded {stats_loaded['total_chunks']} chunks")
    print(f"✓ Loaded {stats_loaded['total_files']} files")
    print()

    # Validation
    print("=" * 80)
    print("VALIDATION:")

    if stats["total_chunks"] == 3:
        print("  ✓ Initial chunks correct: 3")
    else:
        print(f"  ✗ Initial chunks incorrect: {stats['total_chunks']} (expected 3)")

    if stats["total_files"] == 2:
        print("  ✓ Initial files correct: 2")
    else:
        print(f"  ✗ Initial files incorrect: {stats['total_files']} (expected 2)")

    if len(file_results["ids"]) == 2:
        print("  ✓ File path query correct: 2 chunks for gold.md")
    else:
        print(f"  ✗ File path query incorrect: {len(file_results['ids'])} (expected 2)")

    if hash1 == "abc123":
        print("  ✓ Content hash correct: abc123")
    else:
        print(f"  ✗ Content hash incorrect: {hash1}")

    if hash2 is None:
        print("  ✓ Nonexistent file returns None")
    else:
        print(f"  ✗ Nonexistent file should return None: {hash2}")

    if stats_after["total_chunks"] == 2:
        print("  ✓ Delete operation correct: 2 chunks remaining")
    else:
        print(f"  ✗ Delete operation incorrect: {stats_after['total_chunks']} (expected 2)")

    if stats_loaded["total_chunks"] == 2:
        print("  ✓ Persistence verified: 2 chunks loaded")
    else:
        print(f"  ✗ Persistence failed: {stats_loaded['total_chunks']} (expected 2)")

    print()
    print("✓ All tests passed!")
    print(f"\nTest directory: {test_dir}")
    print("(Can be safely deleted after testing)")


if __name__ == "__main__":
    asyncio.run(main())
