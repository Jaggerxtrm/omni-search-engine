# Bug Fix & Improvement Log - Omni-Search Engine

## Testing Progress
- [x] Environment Check
- [x] Indexing & Chunking
- [x] Embedding Service
- [x] Rerank Service
- [x] Search API
- [x] MCP Tool Integration

## Identified Bugs
| ID | Component | Symptom | Status | Remediation Plan |
|---|---|---|---|---|
| B001 | get_duplicate_content | ValueError: The truth value of an array with more than one element is ambiguous. | FIXED | Handled NumPy array comparisons robustly. Verified after rebuild. |
| B002 | write_note | TypeError: VaultIndexer.index_single_file() missing 2 required positional arguments: 'source_root' and 'source_id' | FIXED | Updated index_single_file calls in server.py. Verified indexing and retrieval. |

## Proposed Improvements
| Component | Suggestion | Rationale |
|---|---|---|
| server.py | Dynamic Source Resolution | File tools (write/append/index) currently hardcode "vault". They should resolve source_id and source_root based on the file path to support Repos/Universal Context. |
| server.py | Flexible Parameter Types | Tools taking floats should accept both int/float explicitly in type hints to avoid FastMCP "Invalid request parameters" when whole numbers are passed. |
| indexer_service.py | AST-based Chunking | Implement the planned AST chunking for code files to improve semantic retrieval of functions/classes. |
