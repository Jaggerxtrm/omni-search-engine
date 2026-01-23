---
name: omni-search-engine
description: This skill should be used when the user asks to "search the vault", "find notes about X", "update knowledge base", "index the vault", "explore the obsidian vault", or use the Omni Search Engine tools. You can also use it to search for additional information if needed during your workflows.
version: 0.1.0
---

# Omni Search Engine Skill

Master the use of the Omni Search Engine MCP server to interact with Obsidian vaults semantically and structurally.

## Overview

The Omni Search Engine provides a suite of tools for semantic exploration, indexing, and content management of Obsidian vaults. It bridges the gap between traditional file-based organization and vector-based semantic retrieval.

## Workflow Selection Guide

Choose the right tool based on your intent:

| Intent | Recommended Tool | Why |
| :--- | :--- | :--- |
| **Concept/Theme Discovery** | `semantic_search` | Uses vector embeddings to find notes related by meaning, even without keyword matches. |
| **Exact File/Pattern Search** | `search_notes` | Fast regex matching on filenames and paths. Best for finding specific known entities. |
| **Content Retrieval** | `read_note` | Fetches full text and rich metadata (tags, links, stats) for a specific note. |
| **Content Creation/Modification** | `write_note` or `append_to_note` | Directly modifies the vault. These tools **auto-index** changes for immediate semantic availability. |
| **System Maintenance** | `reindex_vault` or `get_index_stats` | Use when results feel stale or you need to verify the state of the vector store. |
| **Relation Discovery** | `suggest_links` | Finds related notes to establish new connections within the vault. |

## Recommended Procedures

### 1. Exploratory Search
1. Start with `semantic_search` to find conceptual matches.
2. Review the `similarity_score` to gauge relevance.
3. Use `read_note` on high-relevance paths to extract specific information.

### 2. Information Synthesis
1. Use `search_notes` to find all files in a specific project folder (e.g., `1-projects/`).
2. Read the files to understand current progress.
3. Use `suggest_links` to find related research or background notes.
4. Update the project note using `append_to_note` with new insights.

### 3. Knowledge Base Maintenance
1. Check `get_index_stats` to ensure the number of files matches expectations.
2. If large changes were made externally (not via MCP tools), trigger `reindex_vault`.
3. Verify indexing progress via logs or status checks.

## Critical Success Factors

- **Relative Paths**: Always use paths relative to the vault root (e.g., `Folder/Note.md`). Do not use absolute filesystem paths.
- **Result Limits**: Use `n_results` in `semantic_search` to keep the context window manageable. A limit of 5-10 is usually optimal.
- **Auto-Indexing**: Remember that `write_note`, `append_to_note`, and `delete_note` handle index synchronization automatically. You don't need to manually reindex after using these.
- **Metadata Awareness**: Pay attention to the `metadata` returned by `read_note`. It provides structured access to Obsidian-specific features like tags and wikilinks.

## Detailed References

For more in-depth information on specific aspects of the system, consult the following files:

- **Tools & API**: Refer to [references/tool-definitions.md](./references/tool-definitions.md) for detailed parameter schemas and return types.
- **Best Practices**: See [references/best-practices.md](./references/best-practices.md) for architectural guidelines and efficient search strategies.
- **Workflow Examples**: View [examples/workflow-examples.md](./examples/workflow-examples.md) for concrete scenarios and multi-step tool usage patterns.
