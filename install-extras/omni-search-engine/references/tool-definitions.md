# Tool Definitions Reference

This document provides a detailed reference for the tools exposed by the Omni Search Engine MCP server. All paths used in these tools should be relative to the Obsidian vault root unless otherwise specified.

---

## `semantic_search`

Search the Obsidian vault semantically for notes matching a natural language query.

### Parameters
- `query` (string, required): The natural language search query.
- `n_results` (integer, optional): Number of results to return. Default: `5`.
- `folder` (string, optional): Filter results to a specific folder (e.g., "1-projects/trading").
- `tags` (string, optional): Filter results by a comma-separated string of tags (e.g., "trading,gold").

### Return Structure
Returns a list of dictionaries, each containing:
- `id`: Unique identifier for the chunk.
- `content`: The text content of the match.
- `similarity`: A score representing how well the content matches the query (0 to 1).
- `file_path`: Relative path to the note.
- `note_title`: Title of the note.
- `header_context`: The header hierarchy where the match was found.
- `folder`: The folder containing the note.
- `tags`: List of tags associated with the note.
- `chunk_index`: The index of the chunk within the file.
- `token_count`: Number of tokens in the chunk.

### Usage Tip
Use this for open-ended questions where you don't know the exact keywords but know the general topic.

---

## `suggest_links`

Suggest related notes to link to based on content similarity. This tool is optimized to reuse existing embeddings if the file hasn't changed.

### Parameters
- `note_path` (string, required): Relative path to the target note (e.g., "1-projects/trading.md").
- `n_suggestions` (integer, optional): Maximum number of suggestions to return. Default: `5`.
- `min_similarity` (float, optional): Minimum similarity threshold (0 to 1). Default: `0.5`.
- `exclude_current` (boolean, optional): Whether to exclude the source note from results. Default: `True`.
- `folder` (string, optional): Restrict suggestions to a specific folder.
- `tags` (string, optional): Restrict suggestions to notes with specific tags.

### Return Structure
Returns a list of dictionaries, each containing:
- `file_path`: Path to the suggested note.
- `note_title`: Title of the suggested note.
- `similarity`: Weighted similarity score.
- `reason`: Explanation of why this note was suggested (e.g., related sections).
- `suggested_link`: A formatted Obsidian wikilink (e.g., `[[Note Name#Section]]`).

### Usage Tip
Run this on a newly created or updated note to find relevant connections within your vault.

---

## `index_note`

Index or re-index a specific note to ensure it is available for semantic search.

### Parameters
- `note_path` (string, required): Relative path to the note (e.g., "1-projects/new-note.md").

### Return Structure
- `success`: Boolean indicating if indexing succeeded.
- `file`: The path of the indexed file.
- `chunks_indexed`: The number of chunks generated and stored.

### Usage Tip
Use this after manually modifying a file if auto-indexing (WATCH_MODE) is disabled.

---

## `search_notes`

Find notes matching a regex pattern in the filename or relative path.

### Parameters
- `pattern` (string, required): Case-insensitive regex pattern to match against file paths.
- `root_path` (string, optional): Relative path to restrict the search.
- `max_results` (integer, optional): Maximum number of files to return. Default: `50`.

### Return Structure
Returns a list of strings, each being a relative path to a matching note.

### Usage Tip
Useful for finding files by name or navigating specific subdirectories.

---

## `read_note`

Read the full content and extracted metadata of a note.

### Parameters
- `note_path` (string, required): Relative path to the note (e.g., "1-projects/my-note.md").

### Return Structure
- `success`: Boolean indicating if the read was successful.
- `content`: Full text content of the note.
- `metadata`: A dictionary containing:
    - `note_title`: Title of the note.
    - `folder`: Containing folder.
    - `tags`: All extracted tags.
    - `frontmatter_tags`: Tags from YAML frontmatter.
    - `inline_tags`: Tags found within the body.
    - `wikilinks`: List of internal links.
    - `size_bytes`: File size in bytes.
    - `last_modified`: Timestamp of last modification.

### Usage Tip
Always use relative paths from the vault root.

---

## `write_note`

Create or overwrite a note in the vault. Automatically indexes the note after writing.

### Parameters
- `note_path` (string, required): Relative path to the note.
- `content` (string, required): The full content to write.
- `create_dirs` (boolean, optional): Create parent directories if they don't exist. Default: `True`.

### Return Structure
- `success`: Boolean indicating if the write was successful.
- `file_path`: Path to the file.
- `was_created`: Boolean indicating if a new file was created (vs. overwritten).
- `size_bytes`: Final file size.
- `chunks_indexed`: Number of chunks added to the vector index.

### Usage Tip
This is the primary way to add new knowledge to the vault.

---

## `append_to_note`

Append content to the end of an existing note. Fails if the note does not exist.

### Parameters
- `note_path` (string, required): Relative path to the note.
- `content` (string, required): Content to append.

### Return Structure
- `success`: Boolean status.
- `file_path`: Path to the file.
- `size_bytes`: Final file size.
- `chunks_indexed`: Number of chunks in the updated index.

### Usage Tip
Use this for logging or adding information to cumulative documents without rewriting the entire file.

---

## `delete_note`

Destructive operation to remove a note from both the filesystem and the vector index.

### Parameters
- `note_path` (string, required): Relative path to the note.

### Return Structure
- `success`: Boolean status.
- `file_path`: Path to the deleted file.
- `deleted`: Boolean confirmation.

### Usage Tip
Use with caution. This removes the file and its semantic search representation.

---

## `get_index_stats`

Retrieve high-level statistics about the current vector index.

### Parameters
None.

### Return Structure
- `total_chunks`: Total number of segments in the index.
- `total_files`: Total number of unique files indexed.
- `vault_path`: Absolute path to the vault being indexed.
- `chromadb_path`: Path to the vector database storage.
- `embedding_model`: The model used for generating embeddings.
- `collection_name`: The name of the ChromaDB collection.

### Usage Tip
Use this to verify the server is correctly pointed at your vault and index status.

---

## `get_vault_structure`

Get a directory tree representation of the vault.

### Parameters
- `root_path` (string, optional): Relative path to start from.
- `depth` (integer, optional): Maximum recursion depth. Default: `2`.

### Return Structure
Returns a nested dictionary representing the directory structure. Directories contain other dictionaries or "...", while `.md` files are represented by the string "file".

### Usage Tip
Use this to explore the organization of the vault before performing deeper searches.
