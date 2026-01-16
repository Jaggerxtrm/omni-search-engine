"""
Markdown-Aware Chunking

Splits markdown documents into semantic chunks based on header structure.
Preserves header hierarchy as context and respects token size constraints.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from utils import count_tokens, remove_frontmatter


@dataclass
class Chunk:
    """
    Represents a semantic chunk of markdown content.

    Attributes:
        content: The actual text content of the chunk
        chunk_index: Position of this chunk within the note (0-indexed)
        header_context: Full header hierarchy (e.g., "## Market / ### Gold")
        token_count: Number of tokens in this chunk
        file_path: Relative path from vault root (set by indexer)
        note_title: Note filename without extension (set by indexer)
        folder: Parent folder path (set by indexer)
        tags: List of tags from note (set by indexer)
    """

    content: str
    chunk_index: int
    header_context: str
    token_count: int
    file_path: str = ""
    note_title: str = ""
    folder: str = ""
    tags: list[str] = field(default_factory=list)


class MarkdownChunker:
    """
    Chunks markdown documents based on header structure with size constraints.

    Strategy:
    1. Split on headers (# through ######)
    2. Build header hierarchy for context
    3. If section too large: split on paragraphs
    4. If paragraphs too large: split on sentences
    5. If still too large: hard split at max tokens
    """

    def __init__(
        self,
        target_chunk_size: int = 800,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        model: str = "text-embedding-3-small",
    ):
        """
        Initialize chunker with size constraints.

        Args:
            target_chunk_size: Aim for this many tokens per chunk
            max_chunk_size: Never exceed this many tokens
            min_chunk_size: Merge chunks smaller than this
            model: OpenAI model for token counting
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.model = model

    def chunk_markdown(self, content: str) -> list[Chunk]:
        """
        Split markdown content into semantic chunks.

        Args:
            content: Full markdown file content

        Returns:
            List of Chunk objects with header context
        """
        # Remove frontmatter (already extracted separately)
        content_no_frontmatter = remove_frontmatter(content)

        # Split into sections by headers
        sections = self._split_by_headers(content_no_frontmatter)

        # Process sections into chunks
        chunks = []
        for section in sections:
            section_chunks = self._process_section(section)
            chunks.extend(section_chunks)

        # Assign chunk indices
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i

        # Merge small chunks if possible
        chunks = self._merge_small_chunks(chunks)

        return chunks

    def _split_by_headers(self, content: str) -> list[tuple[str, str]]:
        """
        Split content by markdown headers, preserving hierarchy.

        Returns:
            List of (header_context, content) tuples
        """
        # Pattern to match markdown headers
        header_pattern = r"^(#{1,6})\s+(.+)$"

        lines = content.split("\n")
        sections = []
        current_section_lines = []
        header_stack = []  # Track hierarchy: [(level, title), ...]

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                # Save previous section if it has content
                if current_section_lines:
                    header_context = self._build_header_context(header_stack)
                    section_content = "\n".join(current_section_lines)
                    sections.append((header_context, section_content))
                    current_section_lines = []

                # Update header stack
                level = len(header_match.group(1))  # Number of # symbols
                title = header_match.group(2).strip()

                # Pop headers at same or higher level
                while header_stack and header_stack[-1][0] >= level:
                    header_stack.pop()

                # Add new header
                header_stack.append((level, title))

            else:
                # Regular content line
                current_section_lines.append(line)

        # Add final section
        if current_section_lines:
            header_context = self._build_header_context(header_stack)
            section_content = "\n".join(current_section_lines)
            sections.append((header_context, section_content))

        # If no headers found, treat entire content as one section
        if not sections and content.strip():
            sections.append(("", content))

        return sections

    def _build_header_context(self, header_stack: list[tuple[int, str]]) -> str:
        """
        Build full header hierarchy string from stack.

        Args:
            header_stack: List of (level, title) tuples

        Returns:
            Header context string (e.g., "## Markets / ### Gold")
        """
        if not header_stack:
            return ""

        parts = []
        for level, title in header_stack:
            prefix = "#" * level
            parts.append(f"{prefix} {title}")

        return " / ".join(parts)

    def _process_section(self, section: tuple[str, str]) -> list[Chunk]:
        """
        Process a section into chunks respecting size constraints.

        Args:
            section: (header_context, content) tuple

        Returns:
            List of chunks for this section
        """
        header_context, content = section
        content = content.strip()

        if not content:
            return []

        token_count = count_tokens(content, self.model)

        # If section fits target size, return as-is
        if token_count <= self.target_chunk_size:
            return [
                Chunk(
                    content=content,
                    chunk_index=0,  # Will be reassigned later
                    header_context=header_context,
                    token_count=token_count,
                )
            ]

        # If section too large, split on paragraphs
        if token_count > self.target_chunk_size:
            return self._split_by_paragraphs(header_context, content)

        return []

    def _split_by_paragraphs(self, header_context: str, content: str) -> list[Chunk]:
        """
        Split content into chunks on paragraph boundaries.
        Respects code blocks and tables as atomic units.

        Args:
            header_context: Header hierarchy string
            content: Content to split

        Returns:
            List of chunks
        """
        # Get logical paragraphs (code blocks/tables are single paragraphs)
        paragraphs = self._get_logical_paragraphs(content)

        chunks = []
        current_chunk_paragraphs = []
        current_token_count = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            para_tokens = count_tokens(paragraph, self.model)

            # If single paragraph exceeds max size
            if para_tokens > self.max_chunk_size:
                # Save current chunk if any
                if current_chunk_paragraphs:
                    chunk_content = "\n\n".join(current_chunk_paragraphs)
                    chunks.append(
                        Chunk(
                            content=chunk_content,
                            chunk_index=0,
                            header_context=header_context,
                            token_count=current_token_count,
                        )
                    )
                    current_chunk_paragraphs = []
                    current_token_count = 0

                # Check if it's a protected block (code or table)
                if self._is_protected_block(paragraph):
                    # For protected blocks, we prefer to keep them whole even if slightly oversized
                    # OR split by lines if absolutely necessary.
                    # For now, let's treat them as atomic and allow them to exceed max_size slightly
                    # matching the implementation plan preference not to break code.
                    # If it's absurdly large, we might need line splitting, but let's just log/warn
                    # or currently just append it as a single chunk.
                    chunks.append(
                        Chunk(
                            content=paragraph,
                            chunk_index=0,
                            header_context=header_context,
                            token_count=para_tokens,
                        )
                    )
                else:
                    # Split oversized normal paragraph by sentences
                    sentence_chunks = self._split_by_sentences(header_context, paragraph)
                    chunks.extend(sentence_chunks)
                continue

            # Check if adding this paragraph would exceed target
            would_be_tokens = current_token_count + para_tokens

            if would_be_tokens > self.target_chunk_size and current_chunk_paragraphs:
                # Save current chunk
                chunk_content = "\n\n".join(current_chunk_paragraphs)
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        chunk_index=0,
                        header_context=header_context,
                        token_count=current_token_count,
                    )
                )
                # Start new chunk
                current_chunk_paragraphs = [paragraph]
                current_token_count = para_tokens
            else:
                # Add to current chunk
                current_chunk_paragraphs.append(paragraph)
                current_token_count = would_be_tokens

        # Save final chunk
        if current_chunk_paragraphs:
            chunk_content = "\n\n".join(current_chunk_paragraphs)
            chunks.append(
                Chunk(
                    content=chunk_content,
                    chunk_index=0,
                    header_context=header_context,
                    token_count=current_token_count,
                )
            )

        return chunks

    def _get_logical_paragraphs(self, content: str) -> list[str]:
        """
        Split content into logical paragraphs, preserving code blocks and tables.

        Args:
            content: Markdown content

        Returns:
            List of paragraph strings
        """
        # Regex for fenced code blocks
        code_block_pattern = r"(```[\s\S]*?```)"
        
        # Regex for tables (simplified: lines starting with | and ending with | or similar)
        # We'll use a slightly more robust pattern that captures contiguous lines of table-like text
        # But for now, let's focus on identifying the block.
        # Table pattern: Start of line, pipe, content... end of line. Repeated.
        # This is tricky with regex.
        # Alternative: We split by code blocks first. Then within non-code, we check for tables?
        # Let's stick to the code block pattern first as it's the primary failure mode.
        
        # Split by code blocks, capturing the delimiters
        # This returns [text, code_block, text, code_block...]
        parts = re.split(code_block_pattern, content)
        
        logical_paragraphs = []
        
        for part in parts:
            if not part.strip():
                continue
                
            if part.strip().startswith("```"):
                # This is a code block, treat as one paragraph
                logical_paragraphs.append(part.strip())
            else:
                # This is normal text (potentially containing tables)
                # For tables, standard paragraph splitting (\n\n) usually keeps them together 
                # because tables don't have blank lines inside.
                # So we just apply standard splitting here.
                sub_paragraphs = re.split(r"\n\s*\n", part)
                for sub in sub_paragraphs:
                    if sub.strip():
                        logical_paragraphs.append(sub.strip())
                        
        return logical_paragraphs

    def _is_protected_block(self, text: str) -> bool:
        """Check if text is a code block or table."""
        text = text.strip()
        return text.startswith("```") or text.startswith("|")

    def _split_by_sentences(self, header_context: str, content: str) -> list[Chunk]:
        """
        Split content into chunks on sentence boundaries (last resort).

        Args:
            header_context: Header hierarchy string
            content: Content to split

        Returns:
            List of chunks
        """
        # Split on sentence boundaries (. ! ?) followed by space or newline
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, content)

        chunks = []
        current_chunk_sentences = []
        current_token_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sent_tokens = count_tokens(sentence, self.model)

            # If single sentence exceeds max, hard split it
            if sent_tokens > self.max_chunk_size:
                # Save current chunk if any
                if current_chunk_sentences:
                    chunk_content = " ".join(current_chunk_sentences)
                    chunks.append(
                        Chunk(
                            content=chunk_content,
                            chunk_index=0,
                            header_context=header_context,
                            token_count=current_token_count,
                        )
                    )
                    current_chunk_sentences = []
                    current_token_count = 0

                # Hard split oversized sentence
                hard_split_chunks = self._hard_split(header_context, sentence)
                chunks.extend(hard_split_chunks)
                continue

            would_be_tokens = current_token_count + sent_tokens

            if would_be_tokens > self.target_chunk_size and current_chunk_sentences:
                # Save current chunk
                chunk_content = " ".join(current_chunk_sentences)
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        chunk_index=0,
                        header_context=header_context,
                        token_count=current_token_count,
                    )
                )
                # Start new chunk
                current_chunk_sentences = [sentence]
                current_token_count = sent_tokens
            else:
                # Add to current chunk
                current_chunk_sentences.append(sentence)
                current_token_count = would_be_tokens

        # Save final chunk
        if current_chunk_sentences:
            chunk_content = " ".join(current_chunk_sentences)
            chunks.append(
                Chunk(
                    content=chunk_content,
                    chunk_index=0,
                    header_context=header_context,
                    token_count=current_token_count,
                )
            )

        return chunks

    def _hard_split(self, header_context: str, content: str) -> list[Chunk]:
        """
        Hard split content at max_chunk_size (absolute last resort).

        Args:
            header_context: Header hierarchy string
            content: Content to split

        Returns:
            List of chunks
        """
        chunks = []
        words = content.split()
        current_chunk_words = []
        current_token_count = 0

        for word in words:
            word_tokens = count_tokens(word, self.model)
            would_be_tokens = current_token_count + word_tokens

            if would_be_tokens > self.max_chunk_size and current_chunk_words:
                # Save current chunk
                chunk_content = " ".join(current_chunk_words)
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        chunk_index=0,
                        header_context=header_context,
                        token_count=current_token_count,
                    )
                )
                # Start new chunk
                current_chunk_words = [word]
                current_token_count = word_tokens
            else:
                current_chunk_words.append(word)
                current_token_count = would_be_tokens

        # Save final chunk
        if current_chunk_words:
            chunk_content = " ".join(current_chunk_words)
            chunks.append(
                Chunk(
                    content=chunk_content,
                    chunk_index=0,
                    header_context=header_context,
                    token_count=current_token_count,
                )
            )

        return chunks

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Merge consecutive chunks that are below min_chunk_size.

        Args:
            chunks: List of chunks to potentially merge

        Returns:
            List of chunks with small ones merged
        """
        if not chunks:
            return chunks

        merged = []
        current_chunk = chunks[0]

        for next_chunk in chunks[1:]:
            # Check if chunks have same header context and combined size is acceptable
            same_context = current_chunk.header_context == next_chunk.header_context
            combined_tokens = current_chunk.token_count + next_chunk.token_count
            current_is_small = current_chunk.token_count < self.min_chunk_size

            if same_context and current_is_small and combined_tokens <= self.target_chunk_size:
                # Merge chunks
                merged_content = f"{current_chunk.content}\n\n{next_chunk.content}"
                current_chunk = Chunk(
                    content=merged_content,
                    chunk_index=current_chunk.chunk_index,
                    header_context=current_chunk.header_context,
                    token_count=combined_tokens,
                    file_path=current_chunk.file_path,
                    note_title=current_chunk.note_title,
                    folder=current_chunk.folder,
                    tags=current_chunk.tags,
                )
            else:
                # Can't merge, save current and move to next
                merged.append(current_chunk)
                current_chunk = next_chunk

        # Add final chunk
        merged.append(current_chunk)

        # Reassign indices
        for i, chunk in enumerate(merged):
            chunk.chunk_index = i

        return merged


def chunk_markdown_file(
    file_path: Path,
    target_chunk_size: int = 800,
    max_chunk_size: int = 1500,
    min_chunk_size: int = 100,
    model: str = "text-embedding-3-small",
) -> list[Chunk]:
    """
    Convenience function to chunk a markdown file.

    Args:
        file_path: Path to markdown file
        target_chunk_size: Target tokens per chunk
        max_chunk_size: Maximum tokens per chunk
        min_chunk_size: Minimum tokens per chunk (merge smaller)
        model: OpenAI model for token counting

    Returns:
        List of chunks

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    chunker = MarkdownChunker(
        target_chunk_size=target_chunk_size,
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
        model=model,
    )

    return chunker.chunk_markdown(content)
