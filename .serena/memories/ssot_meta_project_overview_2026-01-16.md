---
title: SSOT Project Overview
version: 0.4.0
updated: 2026-01-24T14:30:00+01:00
scope: meta
category: meta
subcategory: overview
domain: [meta, documentation]
changelog:
  - 0.4.0 (2026-01-24): Added Analytics Tools and fixed watcher move/delete consistency.
  - 0.3.0 (2026-01-16): Added Enhanced Chunking capability
  - 0.2.0 (2026-01-16): Updated with Async architecture and CI/CD details
  - 0.1.0 (2026-01-16): Initial overview based on README and codebase analysis
---

## Project Mission
To provide an "agent-first" semantic search system for Obsidian vaults, enabling AI agents to efficiently retrieve, link, and understand knowledge bases via the Model Context Protocol (MCP).

## Core Capabilities
1. **Semantic Search**: Natural language queries over markdown notes.
2. **Auto-Indexing**: Real-time updates via file system watching.
3. **Smart Linking**: Suggested connections based on content similarity.
4. **Efficiency**: Incremental indexing using content hashing to minimize API costs.
5. **Deployment**: Containerized, modular architecture for ease of use.
6. **Code Quality**: Enforced by strict CI pipeline (MyPy, Ruff).
7. **Enhanced Chunking**: Context-aware splitting preserves code blocks and tables.
8. **Analytics**: Tools for identifying orphans, core concepts, and duplicate content.

## Technical Stack
- **Language**: Python 3.13+ (AsyncIO)
- **Protocol**: Model Context Protocol (FastMCP)
- **Vector Store**: ChromaDB (local persistence)
- **Embeddings**: OpenAI (text-embedding-3-small)
- **Watcher**: Watchdog
- **Configuration**: Pydantic Settings
- **Quality Assurance**: Ruff (Linting), MyPy (Type Checking), Pytest (Testing)

## Key Design Principles
- **Modularity**: Service-oriented architecture with strict separation of concerns.
- **Asynchrony**: Non-blocking I/O for responsiveness.
- **Dependency Injection**: Explicit dependencies for better testing and flexibility.
- **Privacy**: Local vector storage; only embeddings are sent to API.
- **Reliability**: Robust error handling and logging.