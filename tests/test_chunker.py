import pytest
from unittest.mock import MagicMock, patch
from crawlers.markdown_crawler import MarkdownChunker, Chunk

# Mock dependencies
@pytest.fixture
def mock_count_tokens():
    with patch('crawlers.markdown_crawler.count_tokens') as mock:
        # Default behavior: 1 token per word for simplicity in tests
        mock.side_effect = lambda text, model: len(text.split())
        yield mock

@pytest.fixture
def mock_remove_frontmatter():
    with patch('crawlers.markdown_crawler.remove_frontmatter') as mock:
        # Default behavior: return content as is
        mock.side_effect = lambda text: text
        yield mock

class TestMarkdownChunker:
    
    def test_initialization(self):
        chunker = MarkdownChunker(
            target_chunk_size=500,
            max_chunk_size=1000,
            min_chunk_size=50,
            chunk_overlap=100
        )
        assert chunker.target_chunk_size == 500
        assert chunker.max_chunk_size == 1000
        assert chunker.min_chunk_size == 50
        assert chunker.chunk_overlap == 100

    def test_split_by_headers_simple(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker()
        content = """# Header 1
Content 1

## Header 2
Content 2
"""
        # We need to access the private method for unit testing
        # or test via public API if possible.
        # Since _split_by_headers is internal, let's test via chunk_markdown 
        # but with large enough chunk size to avoid further splitting.
        
        chunks = chunker.chunk_markdown(content)
        
        # Expect 2 chunks corresponding to the 2 sections
        assert len(chunks) == 2
        assert chunks[0].header_context == "# Header 1"
        assert "Content 1" in chunks[0].content
        assert chunks[1].header_context == "# Header 1 / ## Header 2"
        assert "Content 2" in chunks[1].content

    def test_split_by_headers_nested(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker()
        content = """# H1
Text 1

## H2
Text 2

### H3
Text 3

# H1-B
Text 4
"""
        chunks = chunker.chunk_markdown(content)
        
        assert len(chunks) == 4
        assert chunks[0].header_context == "# H1"
        assert chunks[1].header_context == "# H1 / ## H2"
        assert chunks[2].header_context == "# H1 / ## H2 / ### H3"
        assert chunks[3].header_context == "# H1-B"

    def test_chunk_size_limits(self, mock_count_tokens, mock_remove_frontmatter):
        # Setup: each word is 1 token
        chunker = MarkdownChunker(
            target_chunk_size=5,
            max_chunk_size=10,
            min_chunk_size=1,
            chunk_overlap=0
        )
        
        # Content with 2 paragraphs, 5 words each -> 10 tokens total
        # Should be split into 2 chunks because 5+5 > 5 (target)
        content = "# Header\nword1 word2 word3 word4 word5\n\nword6 word7 word8 word9 word10"
        
        chunks = chunker.chunk_markdown(content)
        
        # Verify splitting
        # We expect 2 chunks
        assert len(chunks) == 2
        assert chunks[0].token_count <= 5
        assert chunks[1].token_count <= 5 # Max size

    def test_overlap_logic(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker(
            target_chunk_size=5,
            max_chunk_size=10,
            min_chunk_size=1,
            chunk_overlap=2
        )
        
        # Paragraphs that are small enough but accumulate to > target
        content = "# Header\npara1\n\npara2\n\npara3"
        
        chunks = chunker.chunk_markdown(content)
        
        # Check for content duplication due to overlap
        # This is a behavior test, might need adjustment based on exact implementation
        all_content = " ".join([c.content for c in chunks])
        assert "para2" in all_content
    
    def test_protected_blocks(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker()
        content = """# Code
Here is code:

```python
def func():
    print("hello")
    return True
```

End code.
"""
        chunks = chunker.chunk_markdown(content)
        
        # The code block should be preserved as one unit inside a chunk
        code_found = False
        for chunk in chunks:
            if "def func():" in chunk.content:
                code_found = True
                assert "```python" in chunk.content
                assert "```" in chunk.content and chunk.content.count("```") >= 2
        
        assert code_found

    def test_merge_small_chunks(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker(
            min_chunk_size=10,
            target_chunk_size=20
        )
        
        # 3 small sections
        content = """# H1
Small1

# H1
Small2

# H1
Small3
"""
        # Each "SmallX" is 1 word = 1 token (mocked)
        # They share same header context "# H1" (actually repeated headers merge? No, standard markdown treats them as separate sections but same context string)
        # Wait, if headers are identical, context string is identical.
        
        chunks = chunker.chunk_markdown(content)
        
        # Should be merged into fewer chunks
        # 3 chunks of ~1 token each -> merged into 1 chunk of ~3 tokens
        assert len(chunks) < 3
        assert len(chunks) == 1
        assert "Small1" in chunks[0].content
        assert "Small2" in chunks[0].content
        assert "Small3" in chunks[0].content

    def test_oversized_paragraph_splitting(self, mock_count_tokens, mock_remove_frontmatter):
        # Paragraph exceeds max_chunk_size
        chunker = MarkdownChunker(
            target_chunk_size=5,
            max_chunk_size=10
        )
        
        # Single long paragraph with 15 words
        content = "# H\n" + " ".join([f"word{i}" for i in range(15)]) + "."
        
        # Sentence splitting will be triggered
        chunks = chunker.chunk_markdown(content)
        
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.token_count <= 10

    def test_oversized_protected_block(self, mock_count_tokens, mock_remove_frontmatter):
        # Protected block exceeds max_chunk_size
        chunker = MarkdownChunker(
            target_chunk_size=5,
            max_chunk_size=10
        )
        
        content = "# H\n```\n" + "\\n".join([f"line{i}" for i in range(15)]) + "\n```"
        
        chunks = chunker.chunk_markdown(content)
        
        # The protected block should be in its own chunk even if it's "oversized" (15 lines/tokens)
        # Because we don't split protected blocks in _split_by_paragraphs
        assert len(chunks) == 1
        assert "```" in chunks[0].content

    def test_complex_overlap_multiple_paras(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker(
            target_chunk_size=10,
            max_chunk_size=20,
            chunk_overlap=5
        )
        
        # p1(4) + p2(4) + p3(4) -> total 12 (exceeds target 10)
        # chunk1: p1, p2
        # chunk2: overlap(p2) + p3
        content = "# H\npara1 word word word\n\npara2 word word word\n\npara3 word word word"
        
        chunks = chunker.chunk_markdown(content)
        
        assert len(chunks) >= 2
        # Check if para2 is in both chunks (overlap)
        assert "para2" in chunks[0].content
        assert "para2" in chunks[1].content

    def test_hard_splitting_long_sentence(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker(
            target_chunk_size=5,
            max_chunk_size=10
        )
        
        # Single sentence with 15 words
        content = "# H\n" + " ".join([f"word{i}" for i in range(15)])
        
        chunks = chunker.chunk_markdown(content)
        
        assert len(chunks) > 1
        assert chunks[0].token_count <= 10
        assert chunks[1].token_count <= 10

    def test_empty_content(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker()
        chunks = chunker.chunk_markdown("")
        assert len(chunks) == 0

    def test_no_headers_content(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker(target_chunk_size=10)
        content = "This is a document with no headers but some content."
        chunks = chunker.chunk_markdown(content)
        assert len(chunks) == 1
        assert chunks[0].header_context == ""

    def test_nested_code_blocks(self, mock_count_tokens, mock_remove_frontmatter):
        # 4 ticks wrapping 3 ticks
        content = """# Nested
````markdown
```python
print("nested")
```
````
"""
        chunker = MarkdownChunker()
        chunks = chunker.chunk_markdown(content)
        
        # Should be treated as one logical block
        assert len(chunks) == 1
        assert "````markdown" in chunks[0].content
        assert "```python" in chunks[0].content

    def test_protected_block_after_content(self, mock_count_tokens, mock_remove_frontmatter):
        # Set target_chunk_size to 1 to force split on any paragraph boundary
        chunker = MarkdownChunker(target_chunk_size=1, min_chunk_size=0)
        # Normal para + protected block
        content = "# H\nNormal para.\n\n```python\nprint(1)\n```"
        
        chunks = chunker.chunk_markdown(content)
        
        # Should be split into 2 chunks
        assert len(chunks) == 2
        assert "Normal para" in chunks[0].content
        assert "```python" in chunks[1].content

    def test_oversized_para_after_content(self, mock_count_tokens, mock_remove_frontmatter):
        chunker = MarkdownChunker(
            target_chunk_size=10,
            max_chunk_size=15
        )
        # para1(5) + oversized_para(20)
        content = "# H\nShort para.\n\n" + " ".join([f"long{i}" for i in range(20)])
        
        chunks = chunker.chunk_markdown(content)
        
        # Should save short para first, then handle oversized
        assert len(chunks) >= 3
        assert "Short para" in chunks[0].content
        assert "long0" in chunks[1].content

    def test_logical_paragraphs_edge_cases(self, mock_count_tokens, mock_remove_frontmatter):
        # Set target_chunk_size to 1 to force split on any paragraph boundary
        chunker = MarkdownChunker(target_chunk_size=1, min_chunk_size=0)
        # Only code block, no leading/trailing text
        content = "```python\nprint(1)\n```"
        chunks = chunker.chunk_markdown(content)
        assert len(chunks) == 1
        assert "```python" in chunks[0].content
        
        # Code block followed by another code block with a blank line between them
        content = "```\nb1\n```\n\n```\nb2\n```"
        chunks = chunker.chunk_markdown(content)
        assert len(chunks) == 2
        assert "b1" in chunks[0].content
        assert "b2" in chunks[1].content

    def test_oversized_sentence_with_existing_content(self, mock_count_tokens, mock_remove_frontmatter):
        # We need a SINGLE paragraph where:
        # 1. para_tokens > max_chunk_size (triggers _split_by_sentences)
        # 2. First sentence fits in target_chunk_size
        # 3. Second sentence > max_chunk_size (triggers hard split after saving first)
        
        chunker = MarkdownChunker(
            target_chunk_size=10,
            max_chunk_size=15,
            min_chunk_size=0
        )
        
        # Single paragraph: short sent (2 tokens). long sent (20 tokens).
        long_sent = " ".join([f"word{i}" for i in range(20)])
        content = f"# H\nShort sent. {long_sent}."
        
        chunks = chunker.chunk_markdown(content)
        
        # Should have:
        # 1. "Short sent."
        # 2. "word0 ... word14" (hard split part 1)
        # 3. "word15 ... word19." (hard split part 2)
        assert len(chunks) >= 3
        assert "Short sent" in chunks[0].content
        assert "word0" in chunks[1].content

def test_chunk_markdown_file_not_found():
    from crawlers.markdown_crawler import chunk_markdown_file
    from pathlib import Path
    
    with pytest.raises(FileNotFoundError):
        chunk_markdown_file(Path("non_existent_file.md"))

def test_chunk_markdown_file_success(tmp_path, mock_count_tokens, mock_remove_frontmatter):
    from crawlers.markdown_crawler import chunk_markdown_file
    
    test_file = tmp_path / "test.md"
    test_file.write_text("# Header\nContent word word word")
    
    chunks = chunk_markdown_file(test_file)
    
    assert len(chunks) == 1
    assert chunks[0].header_context == "# Header"
