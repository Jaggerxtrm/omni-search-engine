"""
Utility Functions

Helper functions for hashing, token counting, path manipulation,
and metadata extraction from markdown files.
"""

import hashlib
import re
from pathlib import Path

import tiktoken
import yaml


def compute_content_hash(content: str) -> str:
    """
    Compute MD5 hash of content for change detection.

    Args:
        content: Text content to hash

    Returns:
        Hexadecimal MD5 hash string
    """
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    """
    Count tokens in text using tiktoken (OpenAI's tokenizer).

    Args:
        text: Text to count tokens for
        model: OpenAI model name for tokenizer

    Returns:
        Number of tokens

    Raises:
        ValueError: If model not supported
    """
    try:
        # Get encoding for the model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base (used by most recent models)
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)
    return len(tokens)


def get_relative_path(file_path: Path, vault_path: Path) -> str:
    """
    Convert absolute file path to vault-relative path.

    Args:
        file_path: Absolute path to file
        vault_path: Absolute path to vault root

    Returns:
        Relative path string (e.g., "1-projects/notes.md")
    """
    try:
        return str(file_path.relative_to(vault_path))
    except ValueError:
        # File is not within vault, return absolute path
        return str(file_path)


def extract_frontmatter_tags(content: str) -> list[str]:
    """
    Extract tags from YAML frontmatter.

    Supports formats:
    - tags: [tag1, tag2, tag3]
    - tags: tag1, tag2
    - tags:
        - tag1
        - tag2

    Args:
        content: Markdown content (full file)

    Returns:
        List of tag strings (without # prefix)
    """
    tags = []

    # Check if content starts with YAML frontmatter (--- delimiter)
    if not content.startswith("---"):
        return tags

    # Find end of frontmatter
    try:
        # Split on first occurrence of --- after the opening ---
        parts = content.split("---", 2)
        if len(parts) < 3:
            return tags

        frontmatter_text = parts[1]

        # Parse YAML
        frontmatter = yaml.safe_load(frontmatter_text)

        if not isinstance(frontmatter, dict):
            return tags

        # Extract tags field
        tags_field = frontmatter.get("tags", [])

        # Handle different formats
        if isinstance(tags_field, list):
            # tags: [tag1, tag2]  or  tags:\n  - tag1\n  - tag2
            for tag in tags_field:
                tag_str = str(tag).strip().lstrip("#")
                if tag_str:
                    tags.append(tag_str)

        elif isinstance(tags_field, str):
            # tags: tag1, tag2  or  tags: #tag1 #tag2
            # Split on commas and/or spaces
            tag_parts = re.split(r"[,\s]+", tags_field)
            for tag in tag_parts:
                tag_str = tag.strip().lstrip("#")
                if tag_str:
                    tags.append(tag_str)

    except (yaml.YAMLError, IndexError):
        # Invalid YAML, return empty list
        pass

    return tags


def extract_inline_tags(content: str) -> list[str]:
    """
    Extract inline hashtags from markdown content.

    Finds patterns like #trading, #gold-market, #macro_economics
    Excludes: URLs, code blocks, headers

    Args:
        content: Markdown content

    Returns:
        List of tag strings (without # prefix)
    """
    tags = []

    # Remove code blocks (```) to avoid matching tags in code
    content_no_code = re.sub(r"```.*?```", "", content, flags=re.DOTALL)

    # Remove inline code (`) to avoid matching tags in code
    content_no_code = re.sub(r"`[^`]+`", "", content_no_code)

    # Remove markdown headers (# at start of line) to avoid false positives
    content_no_code = re.sub(r"^\s*#+\s+.*$", "", content_no_code, flags=re.MULTILINE)

    # Find hashtags: word boundary, #, then alphanumeric/underscore/hyphen
    # Negative lookbehind for URLs (no :// before)
    # Negative lookahead for more # (avoid matching ##, ###, etc.)
    pattern = r"(?<!://.)(?<!\w)#([a-zA-Z0-9_-]+)(?!\w)"

    matches = re.findall(pattern, content_no_code)

    # Deduplicate while preserving order
    seen = set()
    for tag in matches:
        if tag not in seen:
            tags.append(tag)
            seen.add(tag)

    return tags


def get_note_title(file_path: Path) -> str:
    """
    Extract note title from file path (filename without .md extension).

    Args:
        file_path: Path to markdown file

    Returns:
        Note title string
    """
    return file_path.stem  # stem removes extension


def get_folder(file_path: Path, vault_path: Path) -> str:
    """
    Get parent folder path relative to vault root.

    Args:
        file_path: Absolute path to file
        vault_path: Absolute path to vault root

    Returns:
        Parent folder path (e.g., "1-projects/trading")
        Empty string if file is in vault root
    """
    relative_path = get_relative_path(file_path, vault_path)
    folder = str(Path(relative_path).parent)

    # Convert "." (current dir) to empty string
    return "" if folder == "." else folder


def remove_frontmatter(content: str) -> str:
    """
    Remove YAML frontmatter from markdown content.

    Args:
        content: Markdown content with potential frontmatter

    Returns:
        Content without frontmatter
    """
    if not content.startswith("---"):
        return content

    # Find end of frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        return content  # Malformed frontmatter, return as-is

    # Return content after second ---
    return parts[2].lstrip("\n")


def extract_all_tags(content: str) -> list[str]:
    """
    Extract all tags from markdown: frontmatter + inline.

    Args:
        content: Full markdown content

    Returns:
        Deduplicated list of all tags
    """
    frontmatter_tags = extract_frontmatter_tags(content)
    inline_tags = extract_inline_tags(content)

    # Combine and deduplicate
    all_tags = frontmatter_tags + [t for t in inline_tags if t not in frontmatter_tags]

    return all_tags

def extract_wikilinks(content: str) -> list[str]:
    """
    Extract wikilinks from markdown content.

    Handles formats:
    - [[Note Name]] -> Note Name
    - [[Note Name|Alias]] -> Note Name
    - [[Note Name#Header]] -> Note Name
    - [[Note Name#Header|Alias]] -> Note Name

    Args:
        content: Markdown content

    Returns:
        List of unique linked note names (without .md extension)
    """
    # Pattern: [[ (note_name) (separator (alias/header)) ]]
    # [^\]|#]* matches the note name until | or # or ]
    pattern = r"\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]"
    
    matches = re.findall(pattern, content)
    
    # Deduplicate while preserving order
    seen = set()
    links = []
    for link in matches:
        link = link.strip()
        if link and link not in seen:
            links.append(link)
            seen.add(link)
            
    return links
