# Omni Search Engine - Skills Roadmap

This document outlines the proposed complementary skills for the Omni Search Engine MCP server. These skills orchestrate the low-level atomic tools (search, read, write) into high-value knowledge management workflows.

## 1. Tool Inventory
The server provides 15 atomic tools categorized by function:

| Category | Tools |
|----------|-------|
| **Retrieval** | `semantic_search`, `search_notes`, `read_note`, `get_vault_structure` |
| **Content** | `write_note`, `append_to_note`, `delete_note` |
| **Intelligence** | `suggest_links`, `get_duplicate_content`, `get_most_linked_notes` |
| **Maintenance** | `reindex_vault`, `index_note`, `get_index_stats`, `get_vault_statistics`, `get_orphaned_notes` |

## 2. Proposed Skills

### Skill 1: `omni-search:knowledge-gardener`
**Purpose:** Automated maintenance and "weeding" of the knowledge graph.
**Trigger:** Weekly review or user request ("clean up my vault").

**Workflow:**
1.  **Health Check:** Call `get_vault_statistics()` to establish baseline metrics (total files, tags).
2.  **Orphan Hunt:** Call `get_orphaned_notes()` to identify isolated nodes.
3.  **Redundancy Check:** Call `get_duplicate_content(similarity_threshold=0.95)` to find near-exact duplicates.
4.  **Reporting:** Generate a markdown report summarizing the "Health of the Vault" with actionable tasks (e.g., "Merge Note A and Note B", "Link to Orphan Note C").

### Skill 2: `omni-search:topic-synthesizer`
**Purpose:** Deep research and generation of "Map of Content" (MOC) notes.
**Trigger:** "Research X" or "Create a summary of Y".

**Workflow:**
1.  **Search:** Call `semantic_search(topic, n_results=10)` to gather raw material.
2.  **Contextualize:** Call `read_note()` on the most relevant results to get full context.
3.  **Synthesize:** Generate a detailed summary or literature review of the topic, citing sources using Obsidian wikilinks (`[[Note Title]]`).
4.  **Persist:** Call `write_note("topics/{topic}.md", content)` to save the synthesis as a permanent artifact.

### Skill 3: `omni-search:smart-connect`
**Purpose:** Proactive connection discovery for a single note.
**Trigger:** User editing a note and asking "what links to this?" or "what is this related to?".

**Workflow:**
1.  **Analyze:** Call `read_note(target_path)` to understand current content.
2.  **Discovery:**
    *   Call `suggest_links(target_path)` to find semantic matches.
    *   Call `search_notes(pattern=keywords)` to find lexical matches.
3.  **Action:** Present a list of recommended links. User can choose to:
    *   Add inline links.
    *   Call `append_to_note()` to add a "## Related" footer.

### Skill 4: `omni-search:code-context-bridge`
**Purpose:** Bridge the gap between codebase (source) and knowledge base (vault).
**Trigger:** "Find documentation for this code" or "Where is the design doc for this feature?".

**Workflow:**
1.  **Extract Context:** User selects code file or function.
2.  **Cross-Source Search:** Call `semantic_search(code_context, source="vault")` to find relevant design docs.
3.  **Reverse Search:** Call `semantic_search(doc_context, source="current_project")` to find code implementing a design.
4.  **Output:** A mapping showing "Code File X implements Design Note Y".