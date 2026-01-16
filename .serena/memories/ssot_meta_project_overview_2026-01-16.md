---
title: Omni-Search Engine SSOT - Architecture & Overview
version: 0.1.0
updated: 2026-01-16T03:35:00+01:00
category: meta
subcategory: overview
domain: [meta, architecture, project]
branch: main
plan_ref: mcp-refactoring.md
---

## Architecture
- **Type**: MCP Server (Model Context Protocol).
- **Stack**: Python 3.13, FastMCP, ChromaDB, OpenAI Embeddings, Pydantic.
- **Data Flow**:
  - **Ingest**: File Watcher/Manual Trigger → `IndexerService` → `MarkdownCrawler` (Chunking) → `EmbeddingService` (OpenAI) → `SnippetRepository` (ChromaDB).
  - **Query**: Client (Claude) → `server.py` (Tool) → `EmbeddingService` (Query Embedding) → `SnippetRepository` (Vector Search) → Result.

## Infrastructure
- **Containerization**: Podman/Docker.
- **Base Image**: `python:3.13-slim`.
- **Persistence**: 
  - Vault: Read-only bind mount (`/vault`).
  - ChromaDB: Named volume (`obsidian_search_data` mapped to `/data/chromadb`).
- **Config**: Environment variables (`.env`) mapped to `settings.py`.

## Core Capabilities
1. **Semantic Search**: Natural language query -> Vector search.
2. **Smart Indexing**: Content-addressable hashing to skip unchanged files (cost optimization).
3. **Auto-Recovery**: Graceful handling of disconnected clients (`anyio.ClosedResourceError`).
4. **Link Suggestions**: Semantic similarity to suggest related notes.

## Current Status (v1.0 MVP)
- Modular architecture implemented.
- Stable container build.
- Documentation standardized.

## Known Issues
- `anyio.ClosedResourceError` in logs (benign upstream issue).
