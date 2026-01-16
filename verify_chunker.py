
from crawlers.markdown_crawler import MarkdownChunker
from pathlib import Path

def test_integration():
    try:
        chunker = MarkdownChunker()
        
        # Check CHANGELOG.md
        if Path("CHANGELOG.md").exists():
            print("Chunking CHANGELOG.md...")
            with open("CHANGELOG.md", "r") as f:
                content = f.read()
            
            chunks = chunker.chunk_markdown(content)
            print(f"Total chunks: {len(chunks)}")
        else:
            print("CHANGELOG.md not found")

        print("\n--- Testing Hardcoded Complex Case ---")
        complex_content = """
Text
````
```python
nested
```
````
End
"""
        chunks = chunker.chunk_markdown(complex_content)
        for i, c in enumerate(chunks):
            print(f"[{i}] {repr(c.content)}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integration()
