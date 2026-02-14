# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **ShadowObserver**: A background agent that monitors git commits and generates AI-powered session summaries in `dev-log.md`.
    - **Commit-Only Workflow**: Triggers analysis only on git commits to reduce noise.
    - **Qwen Integration**: Uses local Qwen model for generating summaries.
- **Docker Config**: Enabled live code mounting for development.

### Fixed
- **Settings**: Resolved `Pydantic ValidationError` where nested settings didn't receive environment variables.
- **Indexer**: Resolved type errors and metadata handling.
- **Watcher**: Fixed issues with file event handling.

### Refactored
- **ShadowObserver**: Simplified to commit-only workflow from file-event monitoring.

## [0.0.2] - 2026-01-24

### Added
- **Universal Context**: Support for indexing multiple sources simultaneously (e.g., Main Vault + Current Project).
    - **Zero-Config Auto-Discovery**: Automatically indexes the Current Working Directory (`current_project`) if it's not the vault.
    - **Context-Aware Search**: `semantic_search` now supports `source` filtering.
    - **ID Namespacing**: File IDs are now namespaced (`source::path`) to allow same-named files across different projects.
- **Reranking**: Added local reranking using `FlashRank` (default model: `ms-marco-TinyBERT-L-2-v2`).
- **Fix**: Resolved `numpy.float32` JSON serialization error in reranking service.
- **Analytics Tools**:
    - `get_orphaned_notes`: Identifies notes with zero incoming links.
    - `get_most_linked_notes`: Lists top referenced notes (core concepts).
    - `get_duplicate_content`: Detects semantic duplicates using embedding similarity.
- **Watcher Logic Improvements**:
    - `on_moved` events now explicitly remove the old file path from the index before indexing the new one, preventing "ghost notes".
- **Startup Cleanup**:
    - Implemented Offline Move Detection: Automatically scans for and removes index entries for files that were deleted or renamed while the server was offline.

## [0.0.1] - 2026-01-16

### Added
- **Core Search**: `semantic_search` tool for natural language queries over Obsidian vaults.
- **Auto-Indexing**: File watcher (`WATCH_MODE=true`) that incrementally updates the vector index on file changes.
- **Smart Linking**: `suggest_links` tool to recommend related notes based on content similarity.
- **On-Demand Indexing**: `index_note` tool to immediately index specific files.
- **Vault Exploration**: `get_vault_structure` tool to list directory hierarchy.
- **Regex Search**: `search_notes` tool for pattern-based file finding.
- **Diagnostic Tools**: `get_index_stats` to view vector store metrics.
- **Containerization**: Full Docker/Podman support with persistent volumes for data and vault access.
- **Configuration**: Pydantic-based settings management via `.env` file.
- **Documentation**: Comprehensive `README.md`, `USAGE.md`, and `ROADMAP.md`.
- **SSOT Documentation**: Initial set of Single Source of Truth architecture documents in `.serena/memories/`.
- **Enhanced Chunking**: Context-aware splitting algorithm that preserves code blocks (` ```...``` `) and markdown tables as atomic units.

### Changed
- Refactored monolithic script into a modular service-oriented architecture (`services/`, `repositories/`, `dependencies.py`).
- Replaced `print` statements with structured JSON logging (`logger.py`).
- optimized indexing with content hashing to prevent redundant API calls for unchanged files.
- **Link Deduplication**: `suggest_links` now intelligently filters out notes that are already linked in the source document.
- **Metadata**: Indexer now captures `outbound_links` in vector store metadata.
