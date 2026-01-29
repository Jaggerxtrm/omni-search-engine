---
title: SSOT Infrastructure Configuration
version: 0.2.0
updated: 2026-01-24T22:55:00+01:00
scope: infra
category: infra
subcategory: config
domain: [infra, config]
changelog:
  - 0.2.0 (2026-01-24): Added Universal Context and Reranking settings.
  - 0.1.0 (2026-01-16): Configuration schema documentation
---

## Settings Schema (`settings.py`)

Configuration is managed via Pydantic `BaseSettings`, reading from `.env`, `config.yaml`, and environment variables.

### Global Settings
- `OBSIDIAN_VAULT_PATH`: (Legacy/Primary) Path to the main vault.
- `CHROMADB_PATH`: (Default: `chroma_db`) Persistence directory.
- `sources`: List of `SourceConfig` objects (ID, Name, Path, Type). Automatically populated from:
    1. `config.yaml` `sources` list.
    2. `OBSIDIAN_VAULT_PATH` env var (creates "vault" source).
    3. Current Working Directory (creates "current_project" source).

### Universal Context Settings
- `config.yaml`: Optional file to define multiple sources explicitly.

### Embedding Settings (`EMBEDDING_`)
- `API_KEY`: OpenAI API Key.
- `MODEL`: Default `text-embedding-3-small`.
- `BATCH_SIZE`: Default `100`.

### Reranking Settings (`RERANK_`)
- `ENABLED`: `true`/`false` (Default: `true`).
- `MODEL`: Default `ms-marco-TinyBERT-L-2-v2`.

### Chunking Settings (`CHUNK_`)
- `TARGET_CHUNK_SIZE`: Default `1000` tokens.
- `MAX_CHUNK_SIZE`: Default `2000` tokens.
- `MIN_CHUNK_SIZE`: Default `100` tokens.

## Environment Variables
- `WATCH_MODE`: `true`/`false` to enable the filesystem watcher.
- `LOG_LEVEL`: (Implicit via logger) Control verbosity.

## Constraints
- **Validation**: Pydantic ensures paths exist (where applicable) and types are correct.
- **Secrets**: API keys must be loaded from env, never hardcoded.
