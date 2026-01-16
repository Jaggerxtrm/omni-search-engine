---
date_created: Wednesday, January 14th 2026, 9:04:39 pm
date_modified: Thursday, January 15th 2026, 2:12:00 pm
---
# Obsidian Semantic Search - Roadmap

Detailed roadmap and implementation specifications for future enhancements.

## Phase 1: MVP ✅ COMPLETE

All milestones complete. See README for details.

---

## Phase 2: Enhancements
****
### Priority 1: `suggest_links` Tool ✅ COMPLETE

**Goal:** Automatically suggest related notes to link together based on semantic similarity.

**Use Case:**
- User asks: "What notes should I link to this trading strategy note?"
- Returns: List of semantically similar notes with suggested link text

**Implementation:**

1. **New tool in `server.py`:**
```python
@mcp.tool()
def suggest_links(
    note_path: str,
    n_suggestions: int = 5,
    min_similarity: float = 0.5,
    exclude_current: bool = True,
    folder: Optional[str] = None,
    tags: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Suggest related notes to link based on content similarity.

    Args:
        note_path: Path to note (e.g., "1-projects/trading.md")
        n_suggestions: Number of suggestions
        min_similarity: Minimum similarity threshold
        exclude_current: Exclude chunks from same note
    """
```

2. **Logic:**
   - Read target note content
   - Chunk the note (use existing chunker)
   - Generate embeddings for all chunks
   - Query vector store for similar chunks
   - Filter out same-note chunks (if exclude_current=True)
   - Aggregate by note (average similarity across chunks)
   - Return top N notes with similarity scores

3. **Returns:**
```json
[
  {
    "file_path": "notes/gold-markets.md",
    "note_title": "gold-markets",
    "similarity": 0.72,
    "relevant_sections": [
      "## Price Drivers / ### Real Interest Rates"
    ],
    "suggested_link": "[[gold-markets#Real Interest Rates]]"
  }
]
```

**Complexity:** Medium (2-3 hours)
**Dependencies:** None
**Files to modify:** `server.py`

---

### Priority 2: `index_note` Tool ✅ COMPLETE

**Goal:** Index a single note file without reindexing entire vault.

**Use Case:**
- User just created/edited a note
- Want immediate indexing without waiting for full reindex
- "Index the note I just created"

**Implementation:**

1. **New tool in `server.py`:**
```python
@mcp.tool()
def index_note(note_path: str) -> Dict[str, Any]:
    """
    Index a single note file.

    Args:
        note_path: Relative path to note (e.g., "notes/trading.md")

    Returns:
        Success status, chunks created, duration
    """
```

2. **Logic:**
   - Validate note path exists in vault
   - Call `indexer._index_file()` directly
   - Return results similar to `reindex_vault()`

3. **Optimization:**
   - Cache vector store connection
   - Skip vault discovery
   - Only process single file

**Complexity:** Low (30 minutes)
**Dependencies:** None
**Files to modify:** `server.py`

---

### Priority 2: Link Deduplication (Native ChromaDB)

**Goal:** Prevent `suggest_links` from suggesting notes that are *already linked* in the source note.

**Use Case:**
- User asks for suggestions for `Note A`.
- `Note A` already links to `Note B`.
- Search shouldn't suggest `Note B` again.

**Implementation:**
- **Extractor:** Parse wikilinks `[[...]]` during indexing (`indexer.py`).
- **Storage:** Save `outbound_links` list in ChromaDB metadata.
- **Filter:** In `suggest_links`, retrieve `outbound_links` and exclude those IDs from results.

**Complexity:** Medium (2 hours)
**Dependencies:** None (uses existing metadata)

---

### Priority 3: `get_vault_structure` Tool (Serena-inspired)

**Goal:** Allow the agent to explore the vault folder structure recursively.

**Use Case:**
- User asks: "What folders do I have in my vault?"
- Agent needs to understand the directory layout to perform better scoped searches.

**Implementation:**
- **Tool:** `get_vault_structure(relative_path: str = ".", recursive: bool = True)`
- **Logic:** Wrapper around `os.walk` or similar, respecting `.gitignore` and hidden files.
- **Output:** JSON tree or simple list of paths.

**Complexity:** Low (1 hour)
**Dependencies:** None

---

### Priority 3b: Offline Move Detection (Global Hash Lookup)

**Goal:** Efficiently handle file moves/renames that occur while the server is offline.

**Use Case:**
- User renames a folder while the agent is not running.
- On next startup, agent detects "New File" + "Missing Old File".
- Instead of re-embedding, it checks if the content hash exists *anywhere* in the DB.

**Implementation:**
- **Logic:** In `index_vault` (incremental mode), for any new file:
    1. Compute hash.
    2. Query DB for `content_hash`.
    3. If match found: Copy embeddings to new path.
- **Benfits:** Zero API cost for offline reorganization.

**Complexity:** Medium (2 hours)
**Dependencies:** Global hash lookup in `vector_store.py`.

---

### Priority 4: Enhanced Chunking (Code Blocks, Tables)

**Goal:** Improve chunking to respect code block and table boundaries.

**Current Issue:**
- Code blocks can be split mid-block
- Tables can be split mid-row
- Reduces search quality for technical notes

**Implementation:**

1. **Modify `chunker.py`:**
   - Add code block detection: `` ```language ... ``` ``
   - Add table detection: `| col1 | col2 |`
   - Never split within these boundaries

2. **Algorithm changes:**
   - Before splitting on paragraphs, identify code blocks
   - Treat entire code block as atomic unit
   - If code block > max_chunk_size, include as-is but log warning
   - Same logic for tables

3. **New regex patterns:**
```python
# Code blocks
code_block_pattern = r'```[\s\S]*?```'

# Tables (markdown)
table_pattern = r'^\|.+\|$'  # Multiline with M flag
```

4. **Splitting hierarchy update:**
   - Headers → Code blocks/Tables → Paragraphs → Sentences → Words

**Complexity:** Medium (3-4 hours)
**Dependencies:** None
**Files to modify:** `chunker.py`
**Testing:** Update `test_chunker_inline.py` with code block examples

---

### Priority 4: File Watcher for Auto-Sync ✅ COMPLETE

**Goal:** Automatically detect vault changes and reindex modified files.

**Use Case:**
- User edits notes in Obsidian
- Changes automatically reflected in search index
- No manual reindexing needed

**Implementation:**

1. **New module: `file_watcher.py`**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VaultWatcher(FileSystemEventHandler):
    def __init__(self, indexer: VaultIndexer):
        self.indexer = indexer

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.md'):
            # Index the modified file
            self.indexer._index_file(Path(event.src_path))

    def on_created(self, event):
        # Same as on_modified

    def on_deleted(self, event):
        # Delete from vector store
```

2. **Add dependency:**
```txt
watchdog>=3.0.0
```

3. **New tool in `server.py`:**
```python
@mcp.tool()
def start_file_watcher() -> Dict[str, Any]:
    """Start watching vault for changes."""

@mcp.tool()
def stop_file_watcher() -> Dict[str, Any]:
    """Stop watching vault."""
```

4. **Configuration option:**
```yaml
file_watcher:
  enabled: false  # Opt-in for now
  debounce_seconds: 2  # Wait before indexing
  batch_changes: true  # Batch multiple changes
```

**Complexity:** Medium-High (4-5 hours)
**Dependencies:** watchdog library
**Files to create:** `file_watcher.py`
**Files to modify:** `server.py`, `requirements.txt`, `config.yaml`

**Considerations:**
- Debouncing: Don't reindex on every keystroke
- Batching: Group multiple changes
- Performance: Don't impact Obsidian performance
- Container: May need host filesystem access

---

### Priority 5: Analytics Tools

**Goal:** Provide insights about vault structure and content relationships.

**Tools to implement:**

#### 5a. `get_orphaned_notes`

Find notes with no backlinks (not referenced by other notes).

```python
@mcp.tool()
def get_orphaned_notes() -> List[Dict[str, Any]]:
    """
    Find notes that aren't linked to by any other notes.

    Returns:
        List of orphaned notes with metadata
    """
```

**Logic:**
- Parse all notes for wikilinks: `[[note-name]]`
- Build graph of references
- Find notes with in-degree = 0

#### 5b. `get_most_linked_notes`

Find notes that are most frequently referenced.

```python
@mcp.tool()
def get_most_linked_notes(n_results: int = 10) -> List[Dict[str, Any]]:
    """
    Find most frequently linked notes.

    Returns:
        List of notes sorted by link count
    """
```

**Logic:**
- Parse all wikilinks
- Count incoming links per note
- Sort by count

#### 5c. `get_duplicate_content`

Find notes with very similar content (possible duplicates).

```python
@mcp.tool()
def get_duplicate_content(similarity_threshold: float = 0.9) -> List[Dict[str, Any]]:
    """
    Find potentially duplicate notes based on high similarity.

    Returns:
        List of note pairs with similarity scores
    """
```

**Logic:**
- For each note, compute average embedding
- Compare all pairs
- Return pairs above threshold

**Complexity:** Medium (3-4 hours each)
**Dependencies:** None (uses existing infrastructure)
**Files to modify:** `server.py`

---

## Phase 3: Advanced Features

### Feature 1: Reranking for Better Search

**Goal:** Improve search result quality with reranking model.

**Approach:**
- Use Cohere rerank API or similar
- Two-stage search:
  1. ChromaDB: Retrieve 20 candidates (fast)
  2. Reranker: Reorder to top 5 (accurate)

**Benefits:**
- Better relevance ranking
- Handles complex queries better
- Small additional cost (~$0.002/1000 searches)

**Implementation:**
```python
def semantic_search_with_rerank(query: str, n_results: int = 5):
    # Stage 1: Retrieve 4x results from ChromaDB
    candidates = vector_store.query(query_embedding, n_results=n_results * 4)

    # Stage 2: Rerank with Cohere
    reranked = cohere_client.rerank(query=query, documents=candidates)

    # Return top N
    return reranked[:n_results]
```

**Complexity:** Medium (3-4 hours)
**Dependencies:** Cohere SDK
**Cost:** Small per-query cost

---

### Feature 2: Multiple Vault Support

**Goal:** Index and search across multiple Obsidian vaults.

**Use Cases:**
- Personal vault + Work vault
- Multiple projects
- Separate knowledge bases

**Implementation:**

1. **Config changes:**
```yaml
vaults:
  - name: "personal"
    path: "/home/user/personal-vault"
    chromadb_collection: "personal_notes"
  - name: "work"
    path: "/home/user/work-vault"
    chromadb_collection: "work_notes"
```

2. **Tool changes:**
```python
def semantic_search(
    query: str,
    vault: Optional[str] = None  # New parameter
):
    if vault:
        # Search specific vault
    else:
        # Search all vaults, merge results
```

**Complexity:** High (6-8 hours)
**Breaking change:** Config format changes

---

### Feature 3: Graph Visualization

**Goal:** Visualize note relationships as interactive graph.

**Approach:**
- Generate graph data structure from vector similarities
- Output as JSON for D3.js or similar
- Could integrate with Obsidian Graph View

**Implementation:**
```python
@mcp.tool()
def get_similarity_graph(min_similarity: float = 0.5) -> Dict[str, Any]:
    """
    Generate graph of note relationships.

    Returns:
        Nodes (notes) and edges (similarities) in graph format
    """
```

**Complexity:** High (8-10 hours)
**Requires:** Frontend visualization component

---

### Feature 4: Temporal Queries

**Goal:** Search with time-based filters and trends.

**Examples:**
- "What was I writing about in March?"
- "Show recent notes about trading"
- "Notes created this week"

**Implementation:**

1. **Metadata enhancement:**
   - Add created_date to chunks
   - Add last_modified_date

2. **Query filters:**
```python
def semantic_search(
    query: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "similarity"  # or "date"
):
```

3. **ChromaDB where clause:**
```python
where_filter = {
    "modified_date": {"$gte": date_from, "$lte": date_to}
}
```

**Complexity:** Medium (3-4 hours)
**Dependencies:** None

---

### Feature 5: Universal Context (Codebase & Git)

**Goal:** Transform into a "Developer Context Engine" by indexing code and history alongside notes.

#### 5a. Semantic Code Search
Integrate functionality inspired by `zilliztech/claude-context`.
- **Hybrid Search:** Combine Dense Vector Search (semantic) with BM25 (keyword exact match) for best precision.
- **Smart Indexing:**
  - **AST-based Chunking:** Use Abstract Syntax Trees to respect function/class boundaries (Language-aware).
  - **Incremental Updates:** Use Merkle Trees or content hashing for efficient re-indexing.
- **Search:** "Where is authentication handled?" -> Returns `auth.py`

#### 5b. Git History Search
Index commit messages and diffs to allow searching through project history.
- **Query:** "When did I change the login logic?"
- **Source:** `git log -p` parsed into chunks.

#### 5c. Documentation Sync
Integrate with project documentation (e.g. `docs/` folders in repos) and potentially AI memories (Serena).
- Treat external docs as a read-only vault extension.

#### 5d. Cross-Entity Search (Unified Vector Space)
Leverage the single vector store to find code related to notes and vice versa.
- **Query:** "Show code implementing the concept in [[My Note]]"
- **Mechanic:** Search code chunks using the embedding of the note's content.

#### 5e. Context Isolation & Query Scoping
**CRITICAL:** Strict isolation between contexts (Vaults, Repos) by default.
- **Default Behavior:** Search is scoped to the *current active context* (or user's primary vault).
- **Isolation:** Metatada tagging (`source:project-x`) ensures Project A results never appear when searching Project B unless explicitly requested.
- **Explicit Expansion:** User can request "search in ALL projects" or "search in Project Y" via specific tool arguments.

#### 5f. Portability & Configuration (Logical Mounting)
Decouple physical paths from database entries to ensure **100% portability**.
- **Logical Source ID:** DB stores `source_id='trading-bot'` + relative path `src/main.py`.
- **Physical Mapping:** `config.yaml` maps ID to local path.
  ```yaml
  sources:
    - id: "trading-bot"
      path: "/home/user/projects/trading-bot" # Local path
  ```
- **Benefit:** Database can be moved between machines (Home/VPS) without re-indexing; simply update `config.yaml`.

**Complexity:** Very High (20+ hours)
**Prerequisites:** Multiple Vault Support

---

## Implementation Priority Recommendations

**Quick Wins (1-2 days total):**
1. ✅ `index_note` tool - 30 minutes
2. ✅ `suggest_links` tool - 2-3 hours
3. ✅ Temporal queries - 3-4 hours

**High Value (3-5 days):**
4. Enhanced chunking (code blocks, tables) - 3-4 hours
5. Analytics tools - 3-4 hours each
6. Reranking - 3-4 hours

**Longer Term (1-2 weeks):**
7. File watcher - 4-5 hours
8. Multiple vault support - 6-8 hours
9. Graph visualization - 8-10 hours
10. Universal Context (Code/Git) - 20+ hours

---

## Testing Strategy for Phase 2

For each new feature:

1. **Unit tests:** Test individual functions
2. **Integration tests:** Test with real vault data
3. **Performance tests:** Ensure no degradation
4. **Documentation:** Update README and USAGE.md

**Test vault requirements:**
- Include code blocks
- Include tables
- Include wikilinks
- Multiple folders
- Various tags

---

## Breaking Changes to Avoid

**Backwards compatibility:**
- Keep existing tools unchanged
- Add new parameters as optional
- Don't change config format (extend only)
- Keep container interface stable

**Migration path:**
- If breaking changes needed, provide migration script
- Document breaking changes clearly
- Version the API

---

## Performance Considerations

**Phase 2 features impact:**

| Feature | Index Time | Search Time | Storage | API Cost |
|---------|------------|-------------|---------|----------|
| suggest_links | No impact | +200ms | No impact | +1 embedding |
| index_note | -99% | No impact | No impact | Per-file cost |
| Enhanced chunking | +10% | No impact | No impact | No impact |
| File watcher | Continuous | No impact | No impact | Per-change cost |
| Analytics | +5% | +50ms | +10% | No impact |

**Optimization strategies:**
- Cache frequently used data
- Batch operations where possible
- Use incremental updates
- Monitor performance metrics

---

## Documentation Requirements

For each Phase 2 feature:

1. **README.md:** Brief description and benefits
2. **USAGE.md:**
   - How to use
   - Configuration options
   - Example prompts
   - Troubleshooting
3. **Docstrings:** Complete parameter documentation
4. **Tests:** Example usage in test files

---

## Cost Analysis for Phase 2

**Development time estimates:**
- Priority 1-2 (Quick wins): ~1 day
- Priority 3-5 (High value): ~3-4 days
- Phase 3 (Advanced): ~2 weeks

**API cost impact:**
- suggest_links: +1 embedding per call (~$0.00002)
- File watcher: Cost per file edit (same as incremental)
- Reranking: ~$0.002 per search

**Total monthly cost estimate with Phase 2:**
- Base (Phase 1): ~$0.01
- With file watcher: ~$0.02
- With reranking (100 searches): ~$0.03

Still well under $1/month for typical usage.

---

## Decision Points

**Before implementing Phase 2:**

1. **Usage patterns:** Which features would you use most?
2. **Cost sensitivity:** Is $0.03/month acceptable?
3. **Performance:** Is 200-500ms search latency acceptable?
4. **Complexity:** File watcher requires host filesystem access

**Recommended start:** Priority 1-2 (suggest_links, index_note) - highest value, lowest complexity.
