import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from crawlers.markdown_crawler import MarkdownChunker

def test_overlap():
    p = "This is a standard paragraph of about twenty tokens to make testing predictable. "
    c1 = "PART1: " + p * 2 # ~31
    c2 = "PART2: " + p * 2 # ~31
    c3 = "PART3: " + p * 2 # ~31
    content = c1 + "\n\n" + c2 + "\n\n" + c3
    
    print("\nExecuting predictable overlap test (no headers)...")
    chunker = MarkdownChunker(target_chunk_size=80, max_chunk_size=150, chunk_overlap=40)
    chunks = chunker.chunk_markdown(content)
    
    print(f"Total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i} ({chunk.token_count} tokens) ---")
        # print(f"CONTENT: {repr(chunk.content)}")
        print()
        
    assert len(chunks) == 2
    
    # Use normalized comparison
    def is_in(subset, superset):
        return subset.strip() in superset.strip()

    found_in_0 = is_in(c2, chunks[0].content)
    found_in_1 = is_in(c2, chunks[1].content)
    
    print(f"PART2 in Chunk 0: {found_in_0}")
    print(f"PART2 in Chunk 1: {found_in_1}")
    
    if not (found_in_0 and found_in_1):
        print(f"DEBUG c2: {repr(c2.strip())}")
        print(f"DEBUG chunk0: {repr(chunks[0].content.strip())}")

    assert found_in_0 and found_in_1, "PART2 should be in both chunks"
    print("✓ Overlap verified.")

if __name__ == "__main__":
    test_overlap()
