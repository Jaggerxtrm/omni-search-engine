# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- Refactored monolithic script into a modular service-oriented architecture (`services/`, `repositories/`, `dependencies.py`).
- Replaced `print` statements with structured JSON logging (`logger.py`).
- optimized indexing with content hashing to prevent redundant API calls for unchanged files.
- **Link Deduplication**: `suggest_links` now intelligently filters out notes that are already linked in the source document.
- **Metadata**: Indexer now captures `outbound_links` in vector store metadata.
