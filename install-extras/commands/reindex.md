---
description: Trigger a full re-index of the Obsidian vault.
allowedTools:
  - mcp__omni-search-engine__reindex_vault
---

# /reindex

Force the Omni Search Engine to scan the entire vault and update the vector database.

## Usage

1. Call `mcp__omni-search-engine__reindex_vault(force=true)`.
2. Inform the user when the process starts and report the statistics (notes processed, chunks created) when finished.
