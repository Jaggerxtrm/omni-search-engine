---
title: SSOT Infrastructure Configuration
version: 0.1.0
updated: 2026-01-16T10:00:00+01:00
scope: infra
category: infra
subcategory: config
domain: [infra, config]
changelog:
  - 0.1.0 (2026-01-16): Configuration schema documentation
---

## Settings Schema (`settings.py`)

Configuration is managed via Pydantic `BaseSettings`, reading from `.env` and environment variables.

### Global Settings
- `OBSIDIAN_VAULT_PATH`: (Required) Path to the markdown root.
- `CHROMADB_PATH`: (Default: `chroma_db`) Persistence directory.

### Embedding Settings (`EMBEDDING_`)
- `API_KEY`: OpenAI API Key.
- `MODEL`: Default `text-embedding-3-small`.
- `BATCH_SIZE`: Default `100`.

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
