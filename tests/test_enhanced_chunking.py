
import pytest
from crawlers.markdown_crawler import MarkdownChunker

# Mock large content to exceed target_chunk_size (800 tokens)
# A token is roughly 4 chars. 800 tokens ~ 3200 chars.
# We want something > 800 tokens but < 1500 tokens.

def test_code_block_integrity():
    """
    Test that a code block with internal newlines is NOT split
    even if it exceeds target_chunk_size.
    """
    chunker = MarkdownChunker(target_chunk_size=100, max_chunk_size=500)
    
    # Create a code block with empty lines inside
    # Size: ~20 lines * 10 words = 200 words ~ 250 tokens > 100 target
    code_lines = ["print(f'Line {i}')" for i in range(50)]
    # Insert empty lines to trigger paragraph splitting in old logic
    code_content = ""
    for i, line in enumerate(code_lines):
        code_content += line + "\n"
        if i % 5 == 0:
            code_content += "\n" # Empty line
            
    full_content = f"""
# Header

Here is some text.

```python
{code_content}
```

End text.
"""
    
    chunks = chunker.chunk_markdown(full_content)
    
    # Check if any chunk breaks the code block
    # In the old logic, the code block would be split at \n\n
    # So we would see multiple chunks containing parts of the code
    
    code_chunks = [c for c in chunks if "print(f'Line" in c.content]
    
    # Ideally, it should be 1 chunk if it fits in max_chunk_size (500)
    # Our content is roughly 50 lines * 15 chars = 750 chars ~ 200 tokens. 
    # It fits in 500.
    # But it > 100 (target).
    # Old logic: splits at \n\n. so we'd get multiple chunks.
    # New logic: should keep it one chunk.
    
    assert len(code_chunks) == 1, f"Code block was split into {len(code_chunks)} chunks! Should be 1."
    assert code_chunks[0].content.strip().startswith("```python"), "Chunk should start with code block fence"
    assert code_chunks[0].content.strip().endswith("```"), "Chunk should end with code block fence"

def test_markdown_table_integrity():
    """
    Test that a markdown table is NOT split even if it exceeds target sizes.
    """
    chunker = MarkdownChunker(target_chunk_size=50, max_chunk_size=500)
    
    # Create a large table
    header = "| Col 1 | Col 2 | Col 3 |\n|---|---|---|\n"
    rows = "".join([f"| Row {i} Data 1 | Row {i} Data 2 | Row {i} Data 3 |\n" for i in range(20)])
    
    full_content = f"""
# Table Header

Start text.

{header}{rows}

End text.
"""
    
    # Tables don't usually have \n\n inside, unless user makes malformed tables.
    # But the standard splitter splits on \n\n. 
    # If the table is contiguous lines, the standard splitter treats it as ONE paragraph.
    # So it might logically keep it together... UNLESS it hits "split by sentences"?
    # A table row "| ... |" might look like sentence boundaries if it has punctuation?
    # Or if the paragraph is > max_size.
    
    # Let's force it to be > target but < max. 
    # Current logic: If paragraph > max, split by sentences.
    # If paragraph > target, keep adding paragraphs until target.
    
    # Wait, if the table interacts with surrounding text.
    # This test might pass even with old logic if the table is just one big paragraph block.
    # BUT, we want to ensure we treat it as an ATOMIC block. 
    # Meaning checking that we NEVER split it, even if we are desperate? 
    # Or just that we identify it correctly.
    
    chunks = chunker.chunk_markdown(full_content)
    
    table_chunks = [c for c in chunks if "| Row" in c.content]
    
    # If it was split, we'd have multiple.
    assert len(table_chunks) == 1, f"Table was split into {len(table_chunks)} chunks"
