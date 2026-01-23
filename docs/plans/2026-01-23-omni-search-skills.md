# Omni Search Engine Integration Skill - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Create a comprehensive "Omni Search Engine Integration" skill that enables the agent to autonomously and effectively use the custom MCP tools for semantic search, vault navigation, and note management.

**Architecture:**
- **Plugin Structure:** A local plugin directory `omni-search-skills/`.
- **Skill:** `omni-search-skills/skills/omni-search-engine/`
  - `SKILL.md`: Core logic, triggers, and high-level workflows.
  - `references/tool-definitions.md`: Detailed API reference for the tools (extracted from `server.py`).
  - `references/best-practices.md`: Guidelines for when to use semantic search vs regex, how to handle read-only errors, etc.
  - `examples/workflow-examples.md`: Concrete examples of complex tasks (e.g., "Research and summarize", "Link maintenance").

**Tech Stack:** Markdown (for skill definition), Claude Code Skill Format.

---

### Task 1: Create Plugin Structure

**Files:**
- Create: `omni-search-skills/.claude-plugin/plugin.json` (Minimal manifest)
- Create: `omni-search-skills/skills/omni-search-engine/` (Directory structure)

**Step 1: Create directories**
```bash
mkdir -p omni-search-skills/.claude-plugin
mkdir -p omni-search-skills/skills/omni-search-engine/{references,examples}
```

**Step 2: Create plugin.json**
```json
{
  "name": "omni-search-skills",
  "version": "0.1.0",
  "description": "Skills for operating the Omni Search Engine MCP tools"
}
```

---

### Task 2: Create Tool Definitions Reference

**Files:**
- Create: `omni-search-skills/skills/omni-search-engine/references/tool-definitions.md`

**Step 1: Extract tool info**
Read `server.py` (already in context) to get exact signatures and docstrings for:
- `semantic_search`
- `suggest_links`
- `index_note`
- `search_notes`
- `read_note`
- `write_note`
- `append_to_note`
- `delete_note`
- `get_index_stats`
- `get_vault_structure`

**Step 2: Write Reference**
Document each tool with:
- Purpose
- Parameters (types, required/optional)
- Return values
- Usage tips (e.g., "Use relative paths")

---

### Task 3: Create Best Practices Reference

**Files:**
- Create: `omni-search-skills/skills/omni-search-engine/references/best-practices.md`

**Content to cover:**
- **Path Handling:** Always use relative paths from vault root.
- **Search Strategy:** Use `semantic_search` for concepts, `search_notes` (regex) for specific filenames/patterns.
- **Indexing:** Note that `write_note` auto-indexes, but external changes might require `reindex_vault`.
- **Docker vs Local:** Reminder about checking environment if paths fail.
- **Resource Usage:** Don't read entire vault; use search tools to narrow down.

---

### Task 4: Create Workflow Examples

**Files:**
- Create: `omni-search-skills/skills/omni-search-engine/examples/workflow-examples.md`

**Scenarios:**
1.  **"Find notes about X and summarize":** `semantic_search` -> `read_note` (top results) -> Summarize.
2.  **"Find orphan notes":** `get_vault_statistics` (if available) or strategy using `search_notes` and checking links.
3.  **"Update documentation":** `read_note` -> `write_note`.

---

### Task 5: Create SKILL.md (The Core)

**Files:**
- Create: `omni-search-skills/skills/omni-search-engine/SKILL.md`

**Step 1: Frontmatter**
```yaml
---
name: omni-search-engine
description: This skill should be used when the user asks to "search the vault", "find notes about X", "update knowledge base", "index the vault", "explore the obsidian vault", or use the Omni Search Engine tools.
version: 0.1.0
---
```

**Step 2: Body**
- Overview of the system.
- **Workflow Selection Guide:**
    - "If looking for concepts... do X"
    - "If looking for specific files... do Y"
    - "If writing content... do Z"
- References to the `references/` files.
- Imperative instructions on how to chain tools.

---

### Task 6: Installation Instructions

**Files:**
- Create: `omni-search-skills/README.md`

**Content:**
- Instructions on how to install this local plugin into Claude Code (e.g., `cc --plugin-dir ./omni-search-skills` or adding to config).
