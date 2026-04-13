from __future__ import annotations

from typing import Any, Callable

from vaultctl.services.audit_service import run_audit
from vaultctl.services.index_service import index_sources
from vaultctl.services.inspect_service import context, find, status, tree
from vaultctl.services.note_service import append_note, delete_note, extract_links, read_note, write_note
from vaultctl.services.search_service import run_search
from vaultctl.services.stats_service import stats


def legacy_tool_adapters() -> dict[str, Callable[..., Any]]:
    return {
        "semantic_search": lambda query, folder=None, source=None, tag=None, status=None, n_results=5: run_search(
            query=query,
            folder=folder,
            source=source,
            tag=tag,
            status=status,
            limit=n_results,
        ),
        "get_full_context": lambda parent_id: context(parent_id),
        "reindex_vault": lambda force=False: index_sources(source=None, full=bool(force)),
        "get_index_stats": lambda: status(),
        "get_vault_statistics": lambda: stats(),
        "suggest_links": lambda note_path: {"links": extract_links(note_path, None)},
        "index_note": lambda note_path: {"indexed": note_path, "changes": index_sources(source=None)},
        "search_notes": lambda query, n_results=5: run_search(query=query, limit=n_results),
        "read_note": lambda note_path: {"content": read_note(note_path, None)},
        "write_note": lambda note_path, content: write_note(note_path, content, None),
        "append_to_note": lambda note_path, content: append_note(note_path, content, None),
        "delete_note": lambda note_path: delete_note(note_path, None),
        "get_vault_structure": lambda root_path=None, max_depth=3: tree(root_path, None, max_depth),
        "get_orphaned_notes": lambda: run_audit("orphans", None, 100),
        "get_most_linked_notes": lambda n_results=10: run_audit("linked", None, n_results),
        "get_duplicate_content": lambda similarity_threshold=0.95: run_audit("duplicates", None, 100),
    }
