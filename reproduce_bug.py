
from crawlers.markdown_crawler import MarkdownChunker



from crawlers.markdown_crawler import MarkdownChunker
from utils import count_tokens, remove_frontmatter
from pathlib import Path

def test_diagnostics():
    print("--- Diagnostics ---")
    
    # 1. Test Token Counting
    text = "Hello World"
    tokens = count_tokens(text)
    print(f"Tokens for '{text}': {tokens}")
    if tokens == 0:
        print("CRITICAL: count_tokens returned 0!")
        
    # 2. Test Frontmatter Removal
    fm_content = "---\ntitle: Test\n---\nReal Content"
    clean = remove_frontmatter(fm_content)
    print(f"Frontmatter removal: '{clean}'")
    if not clean.strip() == "Real Content":
        print("CRITICAL: remove_frontmatter failed!")

def test_reproduction():
    print("\n--- Reproduction ---")
    # Force splitting by setting target size to 1 token
    chunker = MarkdownChunker(target_chunk_size=50, max_chunk_size=1000) 
    
    # Test on REAL file
    real_file = Path("CHANGELOG.md")
    if real_file.exists():
        with open(real_file, "r") as f:
            content = f.read()
        print(f"Chunking {real_file} (len={len(content)})...")
        chunks = chunker.chunk_markdown(content)
        print(f"Chunks generated: {len(chunks)}")
    else:
        print(f"Warning: {real_file} not found.")

    # Test Malformed Code Block
    bad_content = """
# Bad Code Block
```python
print("Never closed")
"""
    print(f"\nChunking unclosed code block (len={len(bad_content)})...")
    chunks = chunker.chunk_markdown(bad_content)
    print(f"Chunks generated: {len(chunks)}")
    for c in chunks:
        print(f"Chunk content: {c.content}")

if __name__ == "__main__":
    test_diagnostics()
    test_reproduction()
