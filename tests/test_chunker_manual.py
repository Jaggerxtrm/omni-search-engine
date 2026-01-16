#!/usr/bin/env python3
"""
Manual test script for the chunker.
Tests with a real file from the vault.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from crawlers.markdown_crawler import MarkdownChunker

# Test with a real file
test_file = Path(
    "/vault/1-projects/03_studio_insegnamento/trading/concetti-schemi/00_Master_Index.md"
)

if test_file.exists():
    print(f"Testing chunker with: {test_file.name}")
    print("=" * 80)

    with open(test_file) as f:
        content = f.read()

    print(f"File size: {len(content)} characters")
    print()

    # Create chunker
    chunker = MarkdownChunker(target_chunk_size=800, max_chunk_size=1500, min_chunk_size=100)

    # Chunk the content
    chunks = chunker.chunk_markdown(content)

    print(f"✓ Created {len(chunks)} chunks")
    print()

    # Display chunk info
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}:")
        print(f"  Header: {chunk.header_context or '(no header)'}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Content preview: {chunk.content[:100]}...")
        print()

    # Statistics
    token_counts = [c.token_count for c in chunks]
    print("Statistics:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Avg tokens: {sum(token_counts) / len(token_counts):.1f}")
    print(f"  Min tokens: {min(token_counts)}")
    print(f"  Max tokens: {max(token_counts)}")
    print(f"  Total tokens: {sum(token_counts)}")

    # Check for issues
    print()
    print("Validation:")
    oversized = [c for c in chunks if c.token_count > 1500]
    if oversized:
        print(f"  ✗ WARNING: {len(oversized)} chunks exceed max size!")
    else:
        print("  ✓ All chunks within max size (1500 tokens)")

    undersized = [c for c in chunks if c.token_count < 100]
    if undersized:
        print(
            f"  ⚠ Note: {len(undersized)} chunks below min size (may be expected for small sections)"
        )
    else:
        print("  ✓ All chunks above min size (100 tokens)")

else:
    print(f"Test file not found: {test_file}")
