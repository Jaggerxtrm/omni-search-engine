---
description: Perform a quick semantic search in the Obsidian vault.
argumentHint: "[query]"
allowedTools:
  - mcp__omni-search-engine__semantic_search
---

# /search

Search the vault semantically for content matching the provided query.

## Usage

1. Call `mcp__omni-search-engine__semantic_search` with the user's query.
2. Present the top 5 results clearly with their titles, relative paths, and similarity scores.
3. Ask if the user wants to read any of the notes found.
