---
title: SSOT Infra Docker Ops
version: 1.1.0
updated: 2026-02-01T02:45:00+01:00
scope: docker, compose, operations
category: infra
subcategory: docker
domain: [infra, docker, devops]
changelog:
  - 1.1.0 (2026-02-01): Added source code bind mount configuration for development mode.
  - 0.1.0 (2026-01-16): Initial Docker operations documentation.
---

# Docker Operations SSOT

## Overview
This document outlines the containerized architecture and operational procedures for the Omni Search Engine.

## Container Architecture
- **Base Image**: `python:3.13-slim`
- **Service Name**: `omni-search-engine`
- **Orchestration**: `docker-compose.yml`

## Volumes & Mounts
The service uses a combination of bind mounts and named volumes:

1.  **Source Code (Development)**: `.:/app:z`
    *   **Purpose**: Live code reloading. Changes on the host are immediately reflected in the container.
2.  **Vault Data**: `${VAULT_PATH}:/vault:rw,Z`
    *   **Purpose**: Access to the Obsidian vault for indexing and monitoring.
3.  **ChromaDB Data**: `chroma_data:/data/chromadb`
    *   **Purpose**: Persistent storage for vector embeddings (named volume).
4.  **Qwen Config**: `~/.qwen:/root/.qwen:rw,Z`
    *   **Purpose**: Authentication for the Qwen AI agent.

## Environment Variables
- `OPENAI_API_KEY`: Required for embeddings.
- `OBSIDIAN_VAULT_PATH`: Internal path `/vault`.
- `CHROMADB_PATH`: Internal path `/data/chromadb`.
- `WATCH_MODE`: `true` to enable the background watcher.
- `SHADOW_AI_DEBOUNCE`: Debounce time for AI analysis (seconds).

## Operational Commands

### Start Service
```bash
docker-compose up -d
```

### Rebuild Image
Required when adding new dependencies to `requirements.txt` or `Dockerfile`:
```bash
docker-compose up -d --build
```

### View Logs
```bash
docker-compose logs -f
```

### Stop Service
```bash
docker-compose down
```