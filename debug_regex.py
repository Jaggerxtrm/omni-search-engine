
import re

def test_split():
    content = """
Here is some text.

```python
def foo():
    print("bar")
```

More text.
"""
    
    # Current pattern
    code_block_pattern = r"(```[\s\S]*?```)"
    
    print(f"--- Testing Pattern: {code_block_pattern} ---")
    parts = re.split(code_block_pattern, content)
    
    print(f"Split parts ({len(parts)}):")
    for i, part in enumerate(parts):
        print(f"[{i}] len={len(part)}: {repr(part)}")

    print("\n--- Testing Logical Paragraphs Logic ---")
    logical_paragraphs = []
    for part in parts:
        if not part.strip():
            continue
            
        if part.strip().startswith("```"):
            print(f"Found code block: {repr(part[:20])}...")
            logical_paragraphs.append(part.strip())
        else:
            print(f"Found text: {repr(part[:20])}...")
            sub = re.split(r"\n\s*\n", part)
            for s in sub:
                if s.strip():
                     logical_paragraphs.append(s.strip())
    
    print("\nResulting Paragraphs:")
    for i, p in enumerate(logical_paragraphs):
        print(f"[{i}] {repr(p)}")

if __name__ == "__main__":
    test_split()
