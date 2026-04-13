from __future__ import annotations

import re
from dataclasses import dataclass

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
TAG_LINE_RE = re.compile(r"^tags\s*:\s*(.+)$", re.MULTILINE)
STATUS_RE = re.compile(r"^status\s*:\s*(.+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^title\s*:\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class ParsedMarkdown:
    title: str
    body: str
    tags: tuple[str, ...]
    status: str | None
    links: tuple[str, ...]
    heading_paths: tuple[str, ...]


def parse_markdown(content: str, fallback_title: str) -> ParsedMarkdown:
    body = content
    frontmatter = ""
    frontmatch = FRONTMATTER_RE.match(content)
    if frontmatch:
        frontmatter = frontmatch.group(1)
        body = content[frontmatch.end() :]

    title_match = TITLE_RE.search(frontmatter)
    title = (title_match.group(1).strip() if title_match else fallback_title).strip('"')

    tags_match = TAG_LINE_RE.search(frontmatter)
    tags = ()
    if tags_match:
        tag_values = tags_match.group(1).strip().strip("[]")
        tags = tuple(sorted({tag.strip().strip('"').strip("'") for tag in tag_values.split(",") if tag.strip()}))

    status_match = STATUS_RE.search(frontmatter)
    status = status_match.group(1).strip().strip('"') if status_match else None

    links = tuple(sorted({match.group(1).strip() for match in WIKILINK_RE.finditer(body)}))
    heading_paths = tuple(match.group(2).strip() for match in HEADING_RE.finditer(body))
    return ParsedMarkdown(title=title, body=body, tags=tags, status=status, links=links, heading_paths=heading_paths)
