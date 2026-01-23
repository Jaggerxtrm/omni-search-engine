# Best Practices for Omni Search Engine

This guide provides recommendations for AI agents interacting with the Omni Search Engine MCP server. Following these practices ensures efficient search, accurate results, and consistent behavior across different deployment environments.

## Path Handling

- **Always Use Relative Paths**: All tools expect paths relative to the vault root (e.g., `1-projects/my-note.md`, `Fleeting/Idea.md`).
- **Consistency Across Environments**:
    - **Local**: Your vault might be at `/home/user/obsidian-vault`.
    - **Docker**: The vault is typically mounted at `/vault`.
- **Why Relative?**: Using relative paths allows your commands to work regardless of whether the server is running locally or in a container. Absolute paths on the host system will fail if the server is in Docker and doesn't share that specific path.

## Search Strategy

The system offers different ways to find information. Choose the one that fits your current need:

### 1. Semantic Search (`semantic_search`)
- **Use for**: Conceptual queries, natural language questions, or finding themes (e.g., "how do I handle errors in Python?", "ideas for a new novel").
- **Mechanism**: Uses vector embeddings to find notes with similar meanings, even if keywords don't match.

### 2. Regex Search (`search_notes`)
- **Use for**: Finding specific filenames, exact strings, or filtering by directory patterns (e.g., finding all files in `2-areas/finance/` using a regex).
- **Mechanism**: Fast pattern matching against filenames and paths.

### 3. Combination
- Start with `semantic_search` to find relevant content.
- If you need to narrow down by folder or specific naming convention, use `search_notes` to verify paths.

## Indexing & Sync

The system strives to keep the vector database in sync with your notes:

- **Automatic Sync**: `write_note`, `append_to_note`, and `delete_note` automatically update the index. You don't need to call `index_note` after using these tools.
- **Manual Indexing**: Use `index_note` or `reindex_vault` only if:
    - Files were modified outside of the MCP tools (e.g., by the user in the Obsidian app while the MCP server wasn't watching).
    - You suspect the index is out of sync with the filesystem.
- **Performance**: `reindex_vault` can be slow for very large vaults. Prefer `index_note` for specific updates.

## Resource Management

To ensure high performance and avoid token limit issues:

- **N-Results**: Limit your `semantic_search` results (default is 5). Start small and expand if needed.
- **Read Sparingly**: Do not read a large volume of notes. Use search results to identify the **top 2-3 most relevant notes** and read only those using `read_note`.
- **Metadata First**: `read_note` returns both content and metadata. Use the metadata (tags, links) to decide if you need to explore further before reading more files.

## Docker & Permissions

If you are running the server via Docker:

- **Vault Mount**: The vault is usually at `/vault`.
- **Write Access**: Ensure the volume is mounted with read-write permissions (`:rw`). If `write_note` or `delete_note` fails with permission errors, check the mount configuration in `docker-compose.yml`.
- **Network**: The server (if in SSE mode) typically listens on port `8765`.

## Summary Checklist
1. Use **relative paths** from the vault root.
2. Use **semantic search** for concepts; **regex search** for patterns.
3. Trust **auto-indexing** for file manipulation tools.
4. **Identify** relevant notes via search before **reading** them.
5. Be aware of the **/vault** mount point in Docker environments.
