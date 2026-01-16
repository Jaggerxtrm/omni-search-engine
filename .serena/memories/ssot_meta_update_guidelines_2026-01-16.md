---
title: SSOT Update & Maintenance Guidelines
version: 0.1.0
updated: 2026-01-16T03:35:00+01:00
scope: documentation-process, taxonomy, naming-conventions
category: meta
subcategory: guidelines
domain: [meta, documentation, process]
applicability: all future SSOT/docs/memories for the project
changelog:
  - 0.1.0 (2026-01-16): Initial guidelines replicated from yfinance-test (v0.3.3) for omni-search-engine.
---

## Purpose
Provide a repeatable process for creating, updating, and versioning Single Source of Truth (SSOT) docs and Serena memories so future agents can extend coverage safely and consistently.

## Versioning Rules
- Start at 0.1.0 for each new SSOT/memory.
- Patch bump (x.y.Z): content edits, clarifications, small additions.
- Minor bump (x.Y.0): new sections, new domains, notable scope increase.
- Major bump (X.0.0): breaking changes in process, structure, or meaning.
- Always update `version` and `updated` in the front matter when changes are made.

## Metadata Requirements
- Front matter must include: title, version, updated (ISO8601 TZ), scope, category, subcategory, domain (tags array); branch/commit refs if summarizing code changes; plan_ref when tied to a plan.
- Use semver consistently via `version` field.

## File Naming Convention
- `ssot_<scope>_<topic>_<date>.md`
- `plan_<type>_<topic>_<date>.md`
- `pattern_<topic>_<date>.md` (optional date if evolving)
- `troubleshoot_<scope>_<topic>_<date>.md`
- `reference_<topic>.md`
- `archive_<topic>_<date>.md` (for deprecated content)

## Update Process (The "Check-out/Check-in" Protocol)
1. **Search**: Use `list_memories` and `read_memory` to find relevant SSOTs.
2. **Review**: Check if the SSOT covers your proposed changes. Is it outdated?
3. **Draft**:
   - If modifying code structure → Update `ssot_meta_project_structure`.
   - If adding new feature → Create new SSOT or update relevant domain SSOT.
4. **Bump**: Increment version number in front matter.
5. **Log**: Add entry to changelog in front matter.
6. **Save**: Write file back to memory storage.

## Taxonomy & Directory Structure
(Physical location of memories is `.serena/memories/` relative to project root)

### Categories
- **meta**: Guidelines, project structure, high-level overviews.
- **infra**: Docker, MCP, API architecture, CI/CD, deployment.
- **data**: Ingestion, schemas, storage repositories.
- **analytics**: Search algorithms, ranking, chunking logic (for search engine).
- **security**: Auth, secrets, permissions.

## Output Directory Taxonomy (if applicable)
- `output/reports/`: Markdown/Text reports.
- `output/dashboards/`: HTML interactive files.
- `output/json/`: Raw data dumps.
- `output/figures/`: PNG/SVG charts.

## Current Inventory (Initial)

### Meta Files
- `ssot_meta_update_guidelines_2026-01-16.md` (v0.1.0) — *This file*
- `ssot_meta_project_structure_2026-01-16.md` (v0.1.0)
- `ssot_meta_project_overview_2026-01-16.md` (v0.1.0)

## Quality Bar & Checks
- Version bumped and `updated` set.
- Scope/title accurate.
- Changes summarized; gaps/next steps listed.
- Related SSOTs cross-referenced (bidirectional where applicable).
- No secrets/credentials; concise summaries instead of large code dumps.
