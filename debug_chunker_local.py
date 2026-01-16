
import re
from dataclasses import dataclass, field

# === MOCK START ===
def count_tokens(text: str, model: str) -> int:
    return len(text.split())  # Approximate for debugging

def remove_frontmatter(text: str) -> str:
    return text  # No-op for now

@dataclass
class Chunk:
    content: str
    chunk_index: int
    header_context: str
    token_count: int
    file_path: str = ""
    note_title: str = ""
    folder: str = ""
    tags: list[str] = field(default_factory=list)

class MarkdownChunker:
    def __init__(self, target_chunk_size=800, max_chunk_size=1500, min_chunk_size=100, model="gpt-4"):
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.model = model

    def _get_logical_paragraphs(self, content: str) -> list[str]:
        # Regex for fenced code blocks with backreference to handle 3+ ticks
        # Captures: 1. Full Block, 2. Delimiter
        code_block_pattern = r"((`{3,})[\s\S]*?\2)"
        
        parts = re.split(code_block_pattern, content)
        # parts will be [text, FULL_BLOCK, DELIMIT, text, FULL_BLOCK, DELIMIT...]
        
        logical_paragraphs = []
        
        for part in parts:
            if not part:
                continue
                
            # Skip standalone delimiters (they are captured group 2)
            # A full block starts with the delimiter, but the standalone delimiter is just the ticks.
            # We can identify the delimiter because it's usually short and equals the start of the previous block?
            # Easier:
            # check if part matches the delimiter pattern strictly?
            # actually re.split returns the captures.
            # If we have `(A(b))`. Split returns `text, Ab, b, text`.
            # We want `Ab`. we don't want `b`.
            
            # Heuristic: If it looks like just ticks/tildes, AND it was captured as group 2, we skip.
            # But the content might be just ticks?
            # Better loop:
            # The structure is deterministic: [text, group1, group2, text, group1, group2...]
            pass

        # Manual iteration to handle groups
        i = 0
        while i < len(parts):
            text_part = parts[i]
            if text_part.strip():
                # Split normal text
                sub_paragraphs = re.split(r"\n\s*\n", text_part)
                for sub in sub_paragraphs:
                    if sub.strip():
                        logical_paragraphs.append(sub.strip())
            
            # Check if there is a block following
            if i + 1 < len(parts):
                block_part = parts[i+1]
                # delimiter_part = parts[i+2] (We ignore this)
                if block_part.strip():
                    logical_paragraphs.append(block_part.strip())
                
                i += 3 # Skip text, block, delim
            else:
                i += 1

        return logical_paragraphs

    def chunk_markdown(self, content: str) -> list[Chunk]:
        paragraphs = self._get_logical_paragraphs(content)
        # Just return paragraphs as chunks for inspection
        return [Chunk(content=p, chunk_index=i, header_context="", token_count=len(p)) for i, p in enumerate(paragraphs)]

# === MOCK END ===

def test_cases():
    cases = {
        "Simple": """
Here is code:
```python
print("hello")
```
End.
""",
        "Indented": """
- List:
  ```python
  def foo():
      pass
  ```
""",
        "Four Backticks": """
````
Code inside 4 ticks
````
""",
        "Unclosed": """
```python
print("oops")
""",
        "Broken Header": """
text

```python

spaced code
```
"""
    }

    chunker = MarkdownChunker()
    
    for name, content in cases.items():
        print(f"\n=== Case: {name} ===")
        chunks = chunker.chunk_markdown(content)
        for i, c in enumerate(chunks):
            print(f"[{i}] {repr(c.content)}")

if __name__ == "__main__":
    test_cases()
