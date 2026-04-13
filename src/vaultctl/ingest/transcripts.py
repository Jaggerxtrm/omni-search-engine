from __future__ import annotations

from vaultctl.ingest.markdown import ParsedMarkdown, parse_markdown


def parse_transcript(content: str, fallback_title: str) -> ParsedMarkdown:
    return parse_markdown(content, fallback_title)
