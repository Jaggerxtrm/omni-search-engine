# Workflow Examples: Omni Search Engine

This guide provides practical, step-by-step examples for common workflows when using the Omni Search Engine MCP server.

## 1. Research and Summarize
Use this workflow to quickly gather information across your entire vault on a specific topic and create a synthesized summary.

### Step 1: Find relevant notes
Perform a semantic search to identify files that contain concepts related to your research topic.

```json
// Tool: mcp__omni-search-engine__semantic_search
{
  "query": "best practices for asynchronous programming in Python",
  "n_results": 5
}
```

### Step 2: Read top results
Examine the content of the most relevant notes returned by the search.

```json
// Tool: mcp__omni-search-engine__read_note
{
  "note_path": "Technical/Python/Async-Patterns.md"
}
```
*(Repeat for top 2-3 results)*

### Step 3: Synthesize and Summarize
Analyze the gathered information and generate a concise summary.

**Example Output:**
> Based on your vault notes (Async-Patterns, Python-Concurrency, and FastAPI-Best-Practices), asynchronous programming in Python should focus on avoiding blocking calls in the main event loop. Key patterns include using `asyncio.gather` for parallel execution and implementing proper error handling within coroutines.

---

## 2. Maintenance - Smart Linking
Keep your vault organized by discovering and adding links between related notes.

### Step 1: Read the current note
Understand the context of the note you want to enhance.

```json
// Tool: mcp__omni-search-engine__read_note
{
  "note_path": "Projects/Project-Alpha-Research.md"
}
```

### Step 2: Discover related content
Use the `suggest_links` tool to find notes with high semantic similarity to your current file.

```json
// Tool: mcp__omni-search-engine__suggest_links
{
  "note_path": "Projects/Project-Alpha-Research.md",
  "n_suggestions": 3
}
```

### Step 3: Add links to the note
Append the recommended links to a "Related Notes" section at the end of the file.

```json
// Tool: mcp__omni-search-engine__append_to_note
{
  "note_path": "Projects/Project-Alpha-Research.md",
  "content": "\n\n## Related Notes\n- [[Technical/Cloud-Architecture]]\n- [[Meetings/2023-11-15-Project-Alpha-Sync]]"
}
```

---

## 3. Vault Exploration
Use this workflow to understand the structure and content of your vault or specific project folders.

### Step 1: View top-level organization
Get an overview of how your vault is structured.

```json
// Tool: mcp__omni-search-engine__get_vault_structure
{
  "depth": 2
}
```

### Step 2: Locate specific files
Use regex search to find files within a specific path or matching a naming convention.

```json
// Tool: mcp__omni-search-engine__search_notes
{
  "pattern": ".*",
  "root_path": "1-projects/Active-Project/"
}
```

### Step 3: Verify index status
Ensure your search index is healthy and covers all your files.

```json
// Tool: mcp__omni-search-engine__get_index_stats
{}
```

**Output Example:**
```json
{
  "total_chunks": 1245,
  "total_files": 150,
  "vault_path": "/home/user/vault",
  "embedding_model": "text-embedding-3-small"
}
```
