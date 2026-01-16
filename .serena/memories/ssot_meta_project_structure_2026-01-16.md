---
title: SSOT Project Structure
version: 0.2.0
updated: 2026-01-16T10:15:00+01:00
scope: architecture
category: meta
subcategory: structure
domain: [meta, structure, architecture]
changelog:
  - 0.2.0 (2026-01-16): Added scripts, tests, and config files
  - 0.1.0 (2026-01-16): Initial capture of project structure
---

## Directory Layout

```
omni-search-engine/
├── api/                  # API endpoints (FastMCP tools)
├── crawlers/             # Content parsers (Markdown)
├── models/               # Data structures (Pydantic)
├── repositories/         # Data access (ChromaDB)
├── services/             # Core business logic
├── tests/                # Test suite (Pytest)
├── scripts/              # CI/CD and maintenance scripts
├── server.py             # Main entry point & MCP tool definitions
├── settings.py           # Configuration (Pydantic)
├── dependencies.py       # Dependency Injection container
├── logger.py             # Centralized logging
├── watcher.py            # File system observer
├── utils.py              # Shared utilities
├── .pre-commit-config.yaml # Git hooks
├── pyproject.toml        # Tool config (Ruff, MyPy)
├── Dockerfile            # Container definition
└── docker-compose.yml    # Deployment configuration
```

## Module Responsibilities

### Core Infrastructure
- `server.py`: Async application lifecycle, MCP tool registration.
- `dependencies.py`: Wires services and repositories (Dependency Injection).
- `settings.py`: Loads and validates configuration.
- `logger.py`: Configures structured logging.

### Services Layer (`services/`)
- `indexer_service.py`: Orchestrates file scanning, chunking, and indexing logic.
- `embedding_service.py`: Handles interaction with OpenAI API.

### Data Layer (`repositories/`)
- `snippet_repository.py`: Manages vector store operations (CRUD, Query) via ChromaDB.

### QA & CI/CD
- `tests/`: Unit and integration tests.
- `scripts/check.sh`: Master script for linting, typing, and testing.
- `.pre-commit-config.yaml`: Pre-commit hook definitions.

### Utilities
- `watcher.py`: Handles real-time file system events.
- `utils.py`: Helpers for hashing, token counting, etc.