# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This is an MCP (Model Context Protocol) server for semantic search in Obsidian vaults. It uses OpenAI embeddings and ChromaDB for vector storage. The system is designed with a service-oriented architecture, dependency injection, and Pydantic-based configuration. It supports both local execution and containerized deployment via Docker/Podman.

## Architecture
- **API Layer**: `server.py` (FastMCP entry point) exposes tools like `semantic_search`, `index_note`, `reindex_vault`.
- **Services Layer**: `services/` contains business logic (`indexer_service`, `embedding_service`).
- **Repositories Layer**: `repositories/` handles data access (`snippet_repository` for ChromaDB).
- **Core Models**: `models/` defines data structures.
- **Configuration**: `settings.py` manages config via Pydantic and environment variables.
- **Dependency Injection**: `dependencies.py` provides singleton instances of services.
- **Watcher**: `watcher.py` monitors the vault for changes (auto-indexing).

## Development Environment

### Setup
1.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure environment:
    - Copy `.env.example` to `.env`
    - Set `OPENAI_API_KEY` and `OBSIDIAN_VAULT_PATH`

### Running the Server
- **Standard Mode (stdio)**:
    ```bash
    python server.py
    ```
- **SSE Mode (HTTP)**:
    ```bash
    python server.py --sse
    # Runs on port 8765
    ```

### Docker/Podman
- Build:
    ```bash
    docker-compose build
    ```
- Run:
    ```bash
    docker-compose up -d
    ```

### Testing
- Run tests (if available - check `tests/` directory):
    ```bash
    pytest
    ```
    *Note: The current file listing shows a `tests` directory, but standard pytest invocation is recommended.*

## Key Files & Directories
- `server.py`: Main application entry point and MCP tool definitions.
- `settings.py`: Configuration schema (Pydantic).
- `services/`: Core logic (indexing, embeddings).
- `repositories/`: Database interactions (ChromaDB).
- `utils.py`: Helpers for hashing, token counting, and path management.
- `docker-compose.yml`: Container orchestration config.

## Coding Standards
- **Architecture**: Follow the Service/Repository pattern. Use `dependencies.py` for wiring components.
- **Configuration**: Use `settings.py` and environment variables for all config. Avoid hardcoding paths or keys.
- **Type Hinting**: Use Python type hints (`typing` module) extensively.
- **Logging**: Use the centralized `logger.py` module.
- **Error Handling**: Catch exceptions in tool definitions and return structured error dictionaries/messages rather than crashing.
- **Security**: Never commit `.env` files or API keys. Use `utils.py` for safe path handling (`get_relative_path`).

## Common Tasks
- **Add a new tool**: Define the function in `server.py`, decorate with `@mcp.tool()`, and implement logic using services from `dependencies.py`.
- **Change embedding model**: Update `settings.py` or set `EMBEDDING_MODEL` env var.
- **Modify chunking**: Adjust `target_chunk_size` in `settings.py` or env vars.
