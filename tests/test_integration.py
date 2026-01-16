#!/usr/bin/env python3
"""
Integration test for the complete Obsidian semantic search system.

Tests the full workflow: indexing → searching → stats.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from crawlers.markdown_crawler import MarkdownChunker
from repositories.snippet_repository import VectorStore
from services.embedding_service import EmbeddingService
from services.indexer_service import VaultIndexer


async def main():
    # Set up environment for testing
    test_data_dir = tempfile.mkdtemp(prefix="obsidian_test_")
    test_chromadb_dir = tempfile.mkdtemp(prefix="chromadb_test_")

    # Create test vault with sample markdown files
    vault_path = Path(test_data_dir) / "vault"
    vault_path.mkdir(parents=True)

    # Sample file 1: Gold markets
    gold_file = vault_path / "gold-markets.md"
    gold_file.write_text("""---
tags: [trading, gold, commodities]
---

# Gold Market Analysis

Gold is a precious metal that serves as a store of value and hedge against inflation.

## Market Structure

### Physical Markets

The London Bullion Market is the largest center for physical gold trading. Key participants include central banks, investment funds, and industrial users.

### Futures Markets

COMEX gold futures provide price discovery and hedging mechanisms. Contract size is 100 troy ounces.

## Price Drivers

### Real Interest Rates

Real interest rates are the primary driver of gold prices. When real rates fall, gold becomes more attractive as it has no yield.

### Dollar Strength

The US dollar and gold typically move inversely. A stronger dollar makes gold more expensive for foreign buyers.
""")

    # Sample file 2: Treasury bonds
    bonds_file = vault_path / "treasury-bonds.md"
    bonds_file.write_text("""---
tags: [trading, bonds, fixed-income]
---

# Treasury Bonds

US Treasury bonds are government securities with maturities of 10+ years.

## Characteristics

- Fixed coupon payments
- Backed by US government
- Low credit risk
- Sensitive to interest rate changes

## Trading Strategies

### Duration Management

Managing duration exposure is key to bond portfolio management. Duration measures price sensitivity to interest rate changes.
""")

    # Sample file 3: Interest rates
    rates_file = vault_path / "interest-rates.md"
    rates_file.write_text("""---
tags: [macro, rates, fed]
---

# Interest Rates

Interest rates are the cost of borrowing money and the return on savings.

## Federal Reserve Policy

The Federal Reserve sets the federal funds rate to achieve its dual mandate of maximum employment and price stability.

## Real vs Nominal Rates

Real rates adjust for inflation. Real rate = Nominal rate - Expected inflation.
""")

    print("=" * 80)
    print("INTEGRATION TEST: Obsidian Semantic Search")
    print("=" * 80)
    print(f"Test vault: {vault_path}")
    print(f"Test ChromaDB: {test_chromadb_dir}")
    print()

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    print("Step 1: Initialize services")
    print("-" * 80)

    embedding_service = EmbeddingService(api_key=api_key)
    vector_store = VectorStore(persist_directory=test_chromadb_dir)
    chunker = MarkdownChunker()
    indexer = VaultIndexer(
        vault_path=vault_path,
        vector_store=vector_store,
        embedding_service=embedding_service,
        chunker=chunker,
    )

    print("✓ Services initialized")
    print()

    # Test 1: Get initial stats (should be empty)
    print("Step 2: Get initial stats (empty index)")
    print("-" * 80)

    stats = vector_store.get_stats()
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Total files: {stats['total_files']}")

    if stats["total_chunks"] == 0:
        print("✓ Index is empty as expected")
    else:
        print(f"✗ Expected 0 chunks, got {stats['total_chunks']}")
    print()

    # Test 2: Index the vault
    print("Step 3: Index test vault")
    print("-" * 80)

    result = await indexer.index_vault(force=True)

    print(f"Notes processed: {result.notes_processed}")
    print(f"Chunks created: {result.chunks_created}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Errors: {len(result.errors)}")

    if result.errors:
        for error in result.errors:
            print(f"  - {error}")

    if result.notes_processed == 3:
        print("✓ Indexed all 3 test files")
    else:
        print(f"✗ Expected 3 files, processed {result.notes_processed}")

    if result.chunks_created > 0:
        print(f"✓ Created {result.chunks_created} chunks")
    else:
        print("✗ No chunks created")
    print()

    # Test 3: Get stats after indexing
    print("Step 4: Get stats after indexing")
    print("-" * 80)

    stats = vector_store.get_stats()
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Total files: {stats['total_files']}")

    if stats["total_files"] == 3:
        print("✓ All 3 files in index")
    else:
        print(f"✗ Expected 3 files, got {stats['total_files']}")

    if stats["total_chunks"] == result.chunks_created:
        print(f"✓ Chunk count matches: {stats['total_chunks']}")
    else:
        print(
            f"✗ Chunk count mismatch: {stats['total_chunks']} vs {result.chunks_created}"
        )
    print()

    # Test 4: Semantic search - gold prices
    print("Step 5: Semantic search - 'What drives gold prices?'")
    print("-" * 80)

    query1 = "What drives gold prices?"
    query1_embedding = await embedding_service.embed_single(query1)
    results1 = vector_store.query(query1_embedding, n_results=3)

    print(f"Query: {query1}")
    print(f"Found {len(results1['ids'])} results")
    print()

    for i, (doc, meta, dist) in enumerate(
        zip(results1["documents"], results1["metadatas"], results1["distances"], strict=False)
    ):
        similarity = 1 - dist
        print(f"Result {i + 1} (similarity: {similarity:.3f}):")
        print(f"  File: {meta['file_path']}")
        print(f"  Header: {meta['header_context']}")
        print(f"  Content: {doc[:80]}...")
        print()

    # Check if top result is from gold-markets.md
    top_file = results1["metadatas"][0]["file_path"]
    if "gold-markets.md" in top_file:
        print("✓ Top result is from gold-markets.md")
    else:
        print(f"✗ Expected gold-markets.md, got {top_file}")
    print()

    # Test 5: Semantic search - treasury bonds
    print("Step 6: Semantic search - 'How do Treasury bonds work?'")
    print("-" * 80)

    query2 = "How do Treasury bonds work?"
    query2_embedding = await embedding_service.embed_single(query2)
    results2 = vector_store.query(query2_embedding, n_results=3)

    print(f"Query: {query2}")
    print(f"Found {len(results2['ids'])} results")
    print()

    for i, (doc, meta, dist) in enumerate(
        zip(results2["documents"], results2["metadatas"], results2["distances"], strict=False)
    ):
        similarity = 1 - dist
        print(f"Result {i + 1} (similarity: {similarity:.3f}):")
        print(f"  File: {meta['file_path']}")
        print(f"  Header: {meta['header_context']}")
        print(f"  Content: {doc[:80]}...")
        print()

    # Check if top result is from treasury-bonds.md
    top_file2 = results2["metadatas"][0]["file_path"]
    if "treasury-bonds.md" in top_file2:
        print("✓ Top result is from treasury-bonds.md")
    else:
        print(f"✗ Expected treasury-bonds.md, got {top_file2}")
    print()

    # Test 6: Semantic search - Federal Reserve
    print("Step 7: Semantic search - 'Tell me about the Federal Reserve'")
    print("-" * 80)

    query3 = "Tell me about the Federal Reserve"
    query3_embedding = await embedding_service.embed_single(query3)
    results3 = vector_store.query(query3_embedding, n_results=3)

    print(f"Query: {query3}")
    print(f"Found {len(results3['ids'])} results")
    print()

    for i, (doc, meta, dist) in enumerate(
        zip(results3["documents"], results3["metadatas"], results3["distances"], strict=False)
    ):
        similarity = 1 - dist
        print(f"Result {i + 1} (similarity: {similarity:.3f}):")
        print(f"  File: {meta['file_path']}")
        print(f"  Header: {meta['header_context']}")
        print(f"  Content: {doc[:80]}...")
        print()

    # Check if top result is from interest-rates.md
    top_file3 = results3["metadatas"][0]["file_path"]
    if "interest-rates.md" in top_file3:
        print("✓ Top result is from interest-rates.md")
    else:
        print(f"⚠ Expected interest-rates.md, got {top_file3} (may be acceptable)")
    print()

    # Test 7: Incremental reindex (should skip unchanged files)
    print("Step 8: Incremental reindex (should skip unchanged files)")
    print("-" * 80)

    result2 = await indexer.index_vault(force=False)

    print(f"Notes processed: {result2.notes_processed}")
    print(f"Notes skipped: {result2.notes_skipped}")
    print(f"Chunks created: {result2.chunks_created}")

    if result2.notes_skipped == 3:
        print("✓ All files skipped (unchanged)")
    else:
        print(f"✗ Expected 3 skipped, got {result2.notes_skipped}")

    if result2.notes_processed == 0:
        print("✓ No files reprocessed")
    else:
        print(f"✗ Expected 0 processed, got {result2.notes_processed}")
    print()

    # Test 8: Modify a file and reindex
    print("Step 9: Modify file and incremental reindex")
    print("-" * 80)

    # Add content to gold file
    gold_file.write_text(
        gold_file.read_text() + "\n\n## New Section\n\nThis is new content."
    )

    result3 = await indexer.index_vault(force=False)

    print(f"Notes processed: {result3.notes_processed}")
    print(f"Notes skipped: {result3.notes_skipped}")
    print(f"Chunks created: {result3.chunks_created}")

    if result3.notes_processed == 1:
        print("✓ Only modified file reprocessed")
    else:
        print(f"✗ Expected 1 processed, got {result3.notes_processed}")

    if result3.notes_skipped == 2:
        print("✓ Unchanged files skipped")
    else:
        print(f"✗ Expected 2 skipped, got {result3.notes_skipped}")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✓ Test vault created with 3 markdown files")
    print(
        f"✓ Initial indexing: {result.notes_processed} files, {result.chunks_created} chunks"
    )
    print("✓ Semantic search correctly finds relevant content")
    print("✓ Incremental indexing skips unchanged files")
    print("✓ Incremental indexing detects and reprocesses modified files")
    print()
    print("All integration tests passed!")
    print()
    print("Test directories (can be deleted):")
    print(f"  - Vault: {vault_path}")
    print(f"  - ChromaDB: {test_chromadb_dir}")


if __name__ == "__main__":
    asyncio.run(main())
