# Obsidian Semantic Search MCP Server

Agent-first semantic search system for Obsidian vaults using OpenAI embeddings, ChromaDB vector store, and FastMCP.

## Features

- 🔍 **Semantic search** across your entire vault
- 🌐 **Universal Context** - Index multiple projects and your current workspace simultaneously
- 🔗 **Smart link suggestions** based on content similarity
- ⚡ **Async Architecture** - Non-blocking operations for high performance
- 📊 **Markdown-aware chunking** with header hierarchy preservation
- 💾 **Incremental indexing** with content-hash caching (saves API costs)
- 🧹 **Offline Cleanup** - Automatically detects and removes ghost notes on startup
- 📈 **Analytics Tools** - Find orphans, core concepts, and duplicate content
- 🚀 **Local Reranking** - FlashRank integration for superior search relevance
- 🐳 **Containerized** for easy deployment (Podman/Docker)
- 🔒 **Privacy-focused** - vectors stored locally, queries never leave your machine
- 🏗️ **Modular Architecture** - scalable design with Pydantic settings and Dependency Injection
- 🛡️ **Robust CI/CD** - Type checking (MyPy), Linting (Ruff), and Pre-commit hooks

## Status

**Current Progress:** Feature Complete & Containerized ✅

✅ **Completed:**
- **Async Refactor**: Fully asynchronous server and tool execution
- **Code Quality**: Strict type checking (Python 3.13) and linting pipeline
- **Modular Architecture**: Service-based design with Dependency Injection
- **Robust Configuration**: Pydantic-based settings validation
- **Containerization**: Optimized image `omni-search-engine`
- **Core Features**: All MVP tools (Search, Indexing, Stats, Link Suggestions)
- **Auto-Indexing**: Efficient file watcher with coalescing debounce
- **Analytics Suite**: Tools for vault health (Orphans, Duplicates, Ranking)
- **Startup Cleanup**: Self-healing index logic

## Architecture

```
Obsidian Vault (.md files)
    ↓
File Watcher / API Tools (Async)
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
- **Python 3.13+** (for local development)

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

## Universal Context (Multi-Source)

The server now supports indexing multiple sources. By default, it indexes:
1. **Main Vault**: Defined by `VAULT_PATH` in `.env`.
2. **Current Project**: The directory where the server is running (auto-detected).

You can explicitly configure sources in `config.yaml`:
```yaml
sources:
  - id: "my-vault"
    name: "Personal Knowledge Base"
    path: "/home/user/obsidian"
    type: "obsidian"
  - id: "work-repo"
    name: "Work Docs"
    path: "/home/user/work/docs"
    type: "code"
```

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests & Checks

We provide a convenience script to run the full CI suite:

```bash
./scripts/check.sh
```

This runs:
- **Ruff**: Linting and formatting
- **MyPy**: Static type checking
- **Pytest**: Unit and integration tests

## Project Structure

```
obsidian-semantic-search/
├── api/                   # API endpoints (if applicable)
├── crawlers/              # Content parsers (markdown_crawler.py)
├── models/                # Data models
├── repositories/          # Data access (snippet_repository.py)
├── services/              # Business logic (indexer, embedding)
├── tests/                 # Test suite (pytest)
├── scripts/               # CI/CD and utility scripts
├── server.py              # Main FastMCP entry point (Async)
├── settings.py            # Pydantic configuration
├── dependencies.py        # Dependency Injection container
├── logger.py              # Centralized logging
├── watcher.py             # File system watcher
├── .pre-commit-config.yaml # Git hooks configuration
├── pyproject.toml         # Tool configuration (Ruff, MyPy)
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