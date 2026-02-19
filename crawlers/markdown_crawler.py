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
        parent_id: Unique ID of the parent document (set by indexer)
    """

    content: str
    chunk_index: int
    header_context: str
    token_count: int
    file_path: str = ""
    note_title: str = ""
    folder: str = ""
    tags: list[str] = field(default_factory=list)
    parent_id: str = ""


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
        chunk_overlap: int = 150,
        model: str = "text-embedding-3-small",
    ):
        """
        Initialize chunker with size constraints and overlap.

        Args:
            target_chunk_size: Aim for this many tokens per chunk
            max_chunk_size: Never exceed this many tokens
            min_chunk_size: Merge chunks smaller than this
            chunk_overlap: How many tokens should overlap between chunks
            model: OpenAI model for token counting
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.chunk_overlap = chunk_overlap
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

        # Merge small chunks if possible
        chunks = self._merge_small_chunks(chunks)

        # Assign chunk indices
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i

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
        has_headers = False

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                has_headers = True
                # Save previous section if it has content
                if current_section_lines:
                    header_context = self._build_header_context(header_stack)
                    section_content = "\n".join(current_section_lines).strip()
                    if section_content:
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
            section_content = "\n".join(current_section_lines).strip()
            if section_content:
                sections.append((header_context, section_content))

        # If no headers found at all, treat entire content as one section
        if not has_headers and content.strip():
            return [("", content.strip())]

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
        Split content into chunks on paragraph boundaries with overlap.
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
            is_protected = self._is_protected_block(paragraph)

            # FORCE SPLIT for protected blocks to ensure integrity
            # If current paragraph is protected AND we already have content, save current chunk first
            if is_protected and current_chunk_paragraphs:
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

            # If single paragraph exceeds max size
            if para_tokens > self.max_chunk_size:
                # Save current chunk if any (already handled for protected above, but good for normal)
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

                if is_protected:
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
                
                # PREPARE OVERLAP: find how many paragraphs to keep for the next chunk
                # We skip overlap if the current paragraph is protected to avoid splitting it
                overlap_paragraphs = []
                overlap_tokens = 0
                if not is_protected:
                    for p in reversed(current_chunk_paragraphs):
                        # Don't overlap protected blocks into normal chunks as it might break their structure
                        if self._is_protected_block(p):
                            break
                        p_tokens = count_tokens(p, self.model)
                        if overlap_tokens + p_tokens <= self.chunk_overlap:
                            overlap_paragraphs.insert(0, p)
                            overlap_tokens += p_tokens
                        else:
                            break
                
                # Start new chunk with overlap + current paragraph
                current_chunk_paragraphs = overlap_paragraphs + [paragraph]
                current_token_count = overlap_tokens + para_tokens
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
        # Regex for fenced code blocks with backreference to handle 3+ ticks
        # Captures: 1. Full Block, 2. Delimiter
        # This ensures we match nested blocks correctly (e.g. 4 ticks wrapping 3 ticks)
        code_block_pattern = r"((`{3,})[\s\S]*?\2)"
        
        # parts will be [text, FULL_BLOCK, DELIMIT, text, FULL_BLOCK, DELIMIT...]
        parts = re.split(code_block_pattern, content)
        
        logical_paragraphs = []
        
        # Iterate manually to handle the capturing groups structure
        i = 0
        while i < len(parts):
            text_part = parts[i]
            if text_part.strip():
                # This is normal text (potentially containing tables)
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
