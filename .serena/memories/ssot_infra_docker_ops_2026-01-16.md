---
title: SSOT Docker Operations
version: 0.1.0
updated: 2026-01-16T10:00:00+01:00
scope: infra
category: infra
subcategory: docker
domain: [infra, docker, deployment]
changelog:
  - 0.1.0 (2026-01-16): Containerization reference
---

## Container Spec (`Dockerfile`)
- **Base Image**: `python:3.13-slim` (Minimal footprint).
- **Structure**:
    *   Dependencies installed first (layer caching).
    *   Source code copied to `/app`.
    *   Data directory `/data/chromadb` created.
- **Entrypoint**: `python server.py`.

## Orchestration (`docker-compose.yml`)
- **Service**: `omni-search-engine`.
- **Volumes**:
    *   Vault Bind Mount: `${VAULT_PATH}:/vault:ro` (Read-Only safety).
    *   Data Volume: `chroma_data:/data/chromadb` (Persistence).
- **Network**: Exposes port `8765` for SSE mode.
- **Environment**: Passes through API keys and config.

## Operational Commands
- **Build**: `docker-compose build`
- **Run (Detached)**: `docker-compose up -d`
- **Logs**: `docker-compose logs -f`
- **Clean**: `docker-compose down -v` (CAUTION: deletes vector index)
