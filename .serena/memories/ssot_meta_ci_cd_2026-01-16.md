---
title: SSOT CI/CD & Quality Assurance
version: 0.1.0
updated: 2026-01-16T10:15:00+01:00
scope: meta
category: devops
subcategory: ci-cd
domain: [devops, quality, testing]
changelog:
  - 0.1.0 (2026-01-16): Initial documentation of CI/CD pipeline
---

## Overview
The project employs a strict quality assurance pipeline to ensure code reliability, type safety, and consistent formatting. This is enforced via `pre-commit` hooks and local scripts.

## Tools
- **Ruff**: An extremely fast Python linter and formatter. Replaces Flake8, Black, and isort.
- **MyPy**: Static type checker for Python. Enforces type hints across the codebase.
- **Pytest**: The testing framework used for unit and integration tests.
- **Pre-commit**: Manages Git hooks to run checks automatically before commits.

## Configuration Files
- **`pyproject.toml`**: Central configuration for Ruff and MyPy.
  - Target Python version: 3.13
  - MyPy strict mode: Enabled
- **`.pre-commit-config.yaml`**: Defines the hooks (Ruff, MyPy) and their versions.

## Workflows

### 1. Local Development
Developers should install pre-commit hooks immediately after cloning:
```bash
pre-commit install
```
This ensures that every commit is automatically checked for formatting and type errors.

### 2. Manual Verification
To run the full suite manually (including tests), use the helper script:
```bash
./scripts/check.sh
```
This script runs the following in order:
1. `ruff format` (Code formatting)
2. `ruff check --fix` (Linting)
3. `mypy` (Type checking)
4. `pytest` (Unit tests) - *Note: Integration tests may require valid API keys*

## Testing Strategy
- **Unit Tests**: Focus on individual components (e.g., `MarkdownChunker`, `utils`).
- **Integration Tests**: Verify the interaction between services (Indexer -> Embeddings -> VectorStore).
- **Async Testing**: Tests must be compatible with the async architecture (using `pytest-asyncio` if needed).
