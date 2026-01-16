# Obsidian Semantic Search MCP Server

Agent-first semantic search system for Obsidian vaults using OpenAI embeddings, ChromaDB vector store, and FastMCP.

## Features

- 🔍 **Semantic search** across your entire vault
- 🔗 **Smart link suggestions** based on content similarity
- 📊 **Markdown-aware chunking** with header hierarchy preservation
- 💾 **Incremental indexing** with content-hash caching (saves API costs)
- 🐳 **Containerized** for easy deployment (Podman/Docker)
- 🔒 **Privacy-focused** - vectors stored locally, queries never leave your machine

## Status

**Current Progress:** MVP Complete (M1.1 - M1.8) ✅

✅ **Completed:**
- Containerized architecture with Python 3.13
- Configuration system with YAML and env vars
- Utility functions (hashing, token counting, tag extraction)
- Markdown-aware chunker with header hierarchy
- OpenAI embeddings service with retry logic
- ChromaDB vector store with persistent storage
- Vault indexer with incremental updates
- FastMCP server with three tools
- End-to-end integration tests (all passing)

📊 **Test Results:**
- Indexed 3 files → 11 chunks in 4 seconds
- Semantic search: 59-64% similarity on relevant queries
- Incremental indexing: Skips unchanged files (saves API costs)
- Change detection: Reprocesses only modified files

## Architecture

```
Obsidian Vault (.md files)
    ↓
Indexer: Read files → Chunk content → OpenAI embeddings → ChromaDB
    ↓
ChromaDB (persistent local storage)
    ↓
MCP Server exposes tools:
    - semantic_search(query, filters)
    - suggest_links(note_path, threshold)
    - reindex_vault(force)
    - get_index_stats()
```

## Prerequisites

- **Podman** or **Docker** (for containerized deployment)
- **OpenAI API key** (for embeddings)
- **Obsidian vault** with markdown files

## Installation

### 1. Configure Environment

```bash
cd tools/obsidian-semantic-search
cp .env.example .env
# Edit .env: Set OPENAI_API_KEY and VAULT_PATH
```

### 2. Build and Run

```bash
docker-compose up -d --build
```

### 3. MCP Server Configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian-search": {
      "command": "podman",
      "args": [
        "run", "--rm", "-i",
        "-v", "/your/vault/path:/vault:ro",
        "-v", "obsidian_search_data:/data",
        "-e", "OPENAI_API_KEY",
        "obsidian-search:latest"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..." 
      }
    }
  }
}
```

**Important:** Replace paths with your actual vault location and API key.

Then use from Claude Code with natural language:

**Indexing:**
- "Reindex my Obsidian vault"
- "Index all notes (force rebuild)"
- "Update the index with recent changes"

**Searching:**
- "Search my vault for information about gold markets"
- "Find notes related to treasury basis trades"
- "What do my notes say about real interest rates?"

**Stats:**
- **`get_index_stats`**: Get statistics about the current index (file count, chunks).
- **`suggest_links`**: Suggest relevant notes to link to a given note based on semantic similarity.
    - Supports filtering suggestions by **folder** and **tags**.
    - Uses **Smart Caching** to avoid re-generating embeddings for unchanged files (saves API costs).
- **`index_note`**: Forces a re-index of a specific note file.
- **`search_notes`**: Find notes by regex or substring match in file path.
- **`get_vault_structure`**: Get a recursive directory tree of the vault (JSON).
- **Auto-Indexing (Watch Mode)**: Automatically monitors your vault for changes (creation, modification, deletion) and updates the index in real-time.
    - **Coalescing Watcher**: Uses a "trailing edge" debounce (default 30s) to wait for writing to pause before indexing. This handles atomic saves and prevents redundant embeddings during active typing sessions.
    - **Configurable**: Set `DEBOUNCE_SECONDS` in `.env` to adjust the pause duration.


## Testing

Test the chunker:

```bash
podman run --rm --entrypoint python obsidian-search:latest test_chunker_inline.py
```

## Cost Estimation

**Initial index** (450MB vault, ~220 files):
- Estimated tokens: 330,000
- Model: text-embedding-3-small ($0.02/1M tokens)
- **Cost: ~$0.007** (less than 1 cent)

**Incremental updates** (5 notes/day):
- Daily: 7,500 tokens = $0.00015
- **Monthly: ~$0.005** (half a cent)

**Content-hash caching** ensures you only pay for changed/new content!

## Project Structure

```
obsidian-semantic-search/
├── server.py              # FastMCP entry point (in progress)
├── config.py              # Configuration management ✅
├── indexer.py             # Vault indexing orchestration (pending)
├── chunker.py             # Markdown-aware chunking ✅
├── vector_store.py        # ChromaDB wrapper (pending)
├── embeddings.py          # OpenAI API integration (pending)
├── utils.py               # Helper functions ✅
├── config.yaml            # Configuration template ✅
├── Dockerfile             # Container definition ✅
├── docker-compose.yml     # Compose configuration ✅
├── requirements.txt       # Python dependencies ✅
└── tests/                 # Unit tests (pending)
```

## Technical Details

### Chunking Strategy

1. **Split on headers** (`#` through `######`)
2. **Preserve hierarchy** (e.g., "## Section / ### Subsection")
3. **Progressive splitting** if too large:
   - Headers → Paragraphs → Sentences → Words
4. **Merge small chunks** with same context
5. **Size constraints**:
   - Target: 800 tokens
   - Max: 1500 tokens
   - Min: 100 tokens

### Metadata Extracted

Each chunk includes:
```python
{
    "file_path": "1-projects/notes.md",
    "note_title": "notes",
    "chunk_index": 0,
    "header_context": "## Section / ### Subsection",
    "folder": "1-projects",
    "tags": ["trading", "gold"],
    "modified_date": 1704844800.0,
    "content_hash": "a1b2c3d4...",
    "token_count": 750
}
```

### Change Detection

- **MD5 hash** of file content stored in ChromaDB
- **Skip re-embedding** if hash unchanged
- **Incremental reindex** only processes changed files
- **Orphan cleanup** removes deleted files from index

## Development

### Running Tests

```bash
# Test chunker
podman run --rm --entrypoint python obsidian-search:latest test_chunker_inline.py

# Unit tests (coming soon)
podman run --rm --entrypoint pytest obsidian-search:latest tests/
```

### Rebuilding Container

```bash
podman build -t obsidian-search:latest .
```

### Development with docker-compose

```bash
docker-compose up
```

## Troubleshooting

### Container Build Issues

**Problem:** ChromaDB compatibility with Python 3.14
**Solution:** Container uses Python 3.13 (solved)

**Problem:** Permission denied accessing vault
**Solution:** Ensure vault is mounted with `:ro` flag and paths are correct

### API Issues

**Problem:** OpenAI API key not found
**Solution:** Set `OPENAI_API_KEY` environment variable or in config.yaml

**Problem:** Rate limit errors
**Solution:** Retry logic with exponential backoff is built-in (3 attempts)

## Roadmap

### Phase 1: MVP ✅ COMPLETE
- [x] Containerization
- [x] Configuration system
- [x] Utilities
- [x] Markdown chunker
- [x] Embeddings service
- [x] Vector store
- [x] Indexer
- [x] MCP server
- [x] Integration tests

### Phase 2: Enhancements
- [ ] `suggest_links` tool
- [ ] `index_note` tool (single file)
- [ ] Enhanced chunking (code blocks, tables)
- [ ] File watcher for auto-sync
- [ ] Analytics (most-linked, orphaned content)

### Phase 3: Advanced
- [ ] Reranking for better results
- [ ] Multiple vault support
- [ ] Graph visualization
- [ ] Temporal queries

## Contributing

This is a personal project for vault management. Feel free to fork and adapt for your needs.

## License

MIT

## Credits

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [OpenAI](https://openai.com/) - Embeddings API
- [tiktoken](https://github.com/openai/tiktoken) - Token counting

Co-authored with Claude Sonnet 4.5
