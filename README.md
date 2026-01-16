# Obsidian Semantic Search MCP Server

Agent-first semantic search system for Obsidian vaults using OpenAI embeddings, ChromaDB vector store, and FastMCP.

## Features

- 🔍 **Semantic search** across your entire vault
- 🔗 **Smart link suggestions** based on content similarity
- 📊 **Markdown-aware chunking** with header hierarchy preservation
- 💾 **Incremental indexing** with content-hash caching (saves API costs)
- 🐳 **Containerized** for easy deployment (Podman/Docker)
- 🔒 **Privacy-focused** - vectors stored locally, queries never leave your machine
- 🏗️ **Modular Architecture** - scalable design with Pydantic settings and Dependency Injection

## Status

**Current Progress:** Refactoring Complete & Containerized ✅

✅ **Completed:**
- **Modular Architecture**: Service-based design with Dependency Injection
- **Robust Configuration**: Pydantic-based settings validation
- **Containerization**: Optimized image `omni-search-engine` (Python 3.13)
- **Core Features**: All MVP tools (Search, Indexing, Stats, Link Suggestions)
- **Auto-Indexing**: Efficient file watcher with coalescing debounce

## Architecture

```
Obsidian Vault (.md files)
    ↓
File Watcher / API Tools
    ↓
Services Layer (Indexer, Embeddings)
    ↓
Repositories Layer (ChromaDB)
    ↓
MCP Server (FastMCP)
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
# Using Podman Compose
podman-compose up -d --build

# Or manual run
podman run -d --name omni-search-engine \
  --env-file .env \
  -v /path/to/vault:/vault:ro \
  -v chroma_data:/data/chromadb \
  omni-search-engine
```

### 3. MCP Server Configuration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omni-search-engine": {
      "command": "podman",
      "args": [
        "run", "--rm", "-i",
        "-v", "/your/vault/path:/vault:ro",
        "-v", "obsidian_search_data:/data/chromadb",
        "-e", "OPENAI_API_KEY",
        "omni-search-engine:latest"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

**Important:** Replace paths with your actual vault location and API key.

## Project Structure

```
obsidian-semantic-search/
├── api/                   # API endpoints (if applicable)
├── crawlers/              # Document parsers (markdown_crawler.py)
├── models/                # Data models
├── repositories/          # Data access (snippet_repository.py)
├── services/              # Business logic (indexer, embedding)
├── server.py              # Main FastMCP entry point
├── settings.py            # Pydantic configuration
├── dependencies.py        # Dependency Injection container
├── logger.py              # Centralized logging
├── watcher.py             # File system watcher
├── Dockerfile             # Container definition
└── docker-compose.yml     # Compose configuration
```

## Troubleshooting

### Runtime Errors
- **`anyio.ClosedResourceError`**: You may see this in logs when clients disconnect. This is a known upstream issue with `anyio>=4.5` and `mcp` interaction. It is generally benign and does not affect server functionality.

### Container Issues
- Ensure you are using the correct image name: `omni-search-engine`.
- Check volume mounts permissions (`:ro` for vault, read-write for `chromadb`).

## License

MIT
