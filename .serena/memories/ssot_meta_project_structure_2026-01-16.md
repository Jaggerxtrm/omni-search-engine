---
title: SSOT Project Structure & Modules
version: 0.1.0
updated: 2026-01-16T03:35:00+01:00
scope: directory-structure, refactoring
category: meta
subcategory: project_structure
domain: [meta, documentation, architecture]
applicability: all developers
changelog:
  - 0.1.0 (2026-01-16): Initial version documenting the modular MCP structure (v1).
---

## Purpose
This document serves as the Single Source of Truth (SSOT) for the project's directory structure, following the major refactoring to a modular MCP architecture.

## Directory Structure Overview

```
omni-search-engine/
├── api/                   # API endpoints (unused in MVP, reserved for future)
├── crawlers/              # Document parsers and chunking logic
│   └── markdown_crawler.py # Markdown processing & hierarchy preservation
├── models/                # Pydantic data models (unused in MVP, reserved)
├── repositories/          # Data access layer
│   └── snippet_repository.py # ChromaDB vector store wrapper
├── services/              # Business logic layer
│   ├── indexer_service.py   # Orchestrates file reading, chunking, embedding
│   └── embedding_service.py # OpenAI embeddings integration
├── server.py              # Main FastMCP server & tool definitions
├── settings.py            # Pydantic configuration & env loading
├── dependencies.py        # Dependency Injection container (lru_cache)
├── logger.py              # Centralized logging configuration
├── watcher.py             # File system watcher (watchdog)
└── tools/                 # Scripts and utilities
```

## Module Responsibilities

### 1. Server (`server.py`)
**Purpose**: Main entry point. Defines `FastMCP` server, registers tools (`semantic_search`, `reindex_vault`, etc.), and manages `lifespan` (startup/shutdown).
**Key Dependencies**: `settings`, `dependencies`.

### 2. Services (`services/`)
**Purpose**: Core business logic.
- `indexer_service.py`: Coordinates the read -> chunk -> embed -> store pipeline.
- `embedding_service.py`: Handles API calls to OpenAI with retry logic.

### 3. Repositories (`repositories/`)
**Purpose**: Data persistence adaptation.
- `snippet_repository.py`: Manages ChromaDB collections, caching, and querying.

### 4. Crawlers (`crawlers/`)
**Purpose**: Parsing raw files into structured chunks.
- `markdown_crawler.py`: Splits markdown by headers, preserves hierarchy, tracks token counts.

### 5. Config & Infrastructure
- `settings.py`: Type-safe configuration using `pydantic-settings`.
- `dependencies.py`: Provides singleton instances of services via `get_` functions.
- `Dockerfile` / `docker-compose.yml`: Containerization logic.

## Best Practices
1. **Dependency Injection**: Use `dependencies.py` to get service instances; avoid global variables in modules.
2. **Configuration**: Use `get_settings()` from `settings.py` rather than reading raw env vars.
3. **Tool Registration**: Add new MCP tools in `server.py` and delegate logic to `services/`.
