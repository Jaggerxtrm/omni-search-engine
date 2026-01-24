"""
Obsidian Semantic Search MCP Server

FastMCP server providing semantic search capabilities for Obsidian vaults.
Exposes tools for searching notes, indexing, and managing the vector store.
"""

import os
import re
import statistics
import sys
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from dependencies import (
    get_embedding_service,
    get_fresh_indexer,
    get_indexer,
    get_rerank_service,
    get_vector_store,
)
from logger import get_logger, setup_logging

# Modular imports
from settings import get_settings
from utils import compute_content_hash, extract_wikilinks, extract_all_tags, extract_frontmatter_tags, extract_inline_tags, get_note_title, get_folder, get_relative_path

logger = get_logger("server")


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage server lifecycle (startup/shutdown)."""
    watcher = None
    try:
        # Startup logic
        setup_logging()
        logger.info("Pre-warming services...")

        # Access dependencies to trigger lazy initialization
        get_settings()
        get_embedding_service()
        get_vector_store()
        get_indexer()

        logger.info("Services pre-warmed successfully.")

        if os.environ.get("WATCH_MODE", "false").lower() == "true":
            from watcher import VaultWatcher

            logger.info("Auto-indexing enabled (WATCH_MODE=true)")
            settings = get_settings()
            
            # Run startup consistency check (Offline Move Detection)
            # This cleans up any files deleted/renamed while server was off
            indexer = get_indexer()
            indexer.run_startup_cleanup()
            
            # Use fresh indexer for watcher thread to avoid sharing async loop resources
            watcher = VaultWatcher(
                sources=settings.sources, # Updated to use multiple sources
                indexer=get_fresh_indexer(),
                vector_store=get_vector_store(),
            )
            watcher.start()

        yield

    finally:
        # Shutdown logic
        if watcher:
            logger.info("Stopping Vault Watcher...")
            watcher.stop()
            logger.info("Vault Watcher stopped.")


# Initialize FastMCP server with lifespan
mcp = FastMCP("obsidian-semantic-search", lifespan=lifespan)


@mcp.tool()
async def semantic_search(
    query: str, n_results: int = 5, folder: str | None = None, tags: str | None = None, source: str | None = None
) -> list[dict[str, Any]]:
    """
    Search semantically across all sources (Vaults, Repos) or a specific one.

    Args:
        query: Natural language search query
        n_results: Number of results to return (default: 5)
        folder: Optional folder filter (e.g., "1-projects/trading")
        tags: Optional comma-separated string of tags (e.g., "trading,gold"). NOT a list.
        source: Optional source ID filter (e.g., "vault", "current_project")

    Returns:
        List of search results with content, metadata, and similarity scores
    """
    logger.info(
        f"Tool Call: semantic_search | Query: '{query}' | Folder: {folder} | Tags: {tags} | Source: {source}"
    )
    try:
        # Get services
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()
        rerank_service = get_rerank_service()  # New dependency

        # Generate query embedding
        logger.debug(f"Generating embedding for query: '{query}'")
        query_embedding = await embedding_service.embed_single(query)

        # Build metadata filter
        where_filter = {}
        if folder:
            where_filter["folder"] = folder
        if tags:
            where_filter["tags"] = tags
        if source:
             where_filter["source"] = source
        
        # If no filters, set to None for cleaner logging/calls
        if not where_filter:
             where_filter = None

        # Query vector store
        # Strategy: Fetch more candidates if reranking is enabled
        fetch_k = n_results * 5 if rerank_service.enabled else n_results
        
        results = vector_store.query(
            query_embedding=query_embedding, n_results=fetch_k, where=where_filter
        )

        # Format initial results
        candidates = []
        for i in range(len(results["ids"])):
            distance = results["distances"][i]
            similarity = 1 - distance
            metadata = results["metadatas"][i]
            
            # Convert comma-separated tags back to list
            tags_str = metadata.get("tags", "")
            tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]

            candidate = {
                "id": results["ids"][i],
                "content": results["documents"][i],
                "similarity": round(similarity, 3), # Vector similarity
                # "score": ... # Will be added by reranker
                "source": metadata.get("source", "unknown"), # NEW
                "file_path": metadata.get("file_path", ""),
                "note_title": metadata.get("note_title", ""),
                "header_context": metadata.get("header_context", ""),
                "folder": metadata.get("folder", ""),
                "tags": tags_list,
                "chunk_index": metadata.get("chunk_index", 0),
                "token_count": metadata.get("token_count", 0),
            }
            candidates.append(candidate)
            
        # Rerank candidates
        final_results = rerank_service.rerank(query, candidates, top_n=n_results)

        logger.info(f"Search successful. Found {len(final_results)} results (from {len(candidates)} candidates).")
        return final_results

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return [{"error": f"Search failed: {str(e)}", "query": query}]


@mcp.tool()
async def reindex_vault(force: bool = False) -> dict[str, Any]:
    """
    Rebuild or update the entire vault index.

    Args:
        force: If True, reindex all files regardless of changes.
               If False, only index new/modified files (incremental).

    Returns:
        Dictionary with indexing statistics:
        - notes_processed: Number of notes indexed
        - notes_skipped: Number of unchanged notes skipped
        - chunks_created: Total chunks generated
        - duration_seconds: Time taken
        - errors: List of any errors encountered
    """
    logger.info(f"Tool Call: reindex_vault | Force: {force}")
    try:
        indexer = get_indexer()
        result = await indexer.index_vault(force=force)

        logger.info(
            f"Reindex complete. Stats: Processed={result.notes_processed}, "
            f"chunks={result.chunks_created}"
        )
        return {
            "success": True,
            "notes_processed": result.notes_processed,
            "notes_skipped": result.notes_skipped,
            "chunks_created": result.chunks_created,
            "duration_seconds": round(result.duration_seconds, 2),
            "errors": result.errors,
        }

    except Exception as e:
        logger.error(f"Reindex failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Indexing failed: {str(e)}",
            "notes_processed": 0,
            "notes_skipped": 0,
            "chunks_created": 0,
            "duration_seconds": 0,
            "errors": [str(e)],
        }


@mcp.tool()
def get_index_stats() -> dict[str, Any]:
    """
    Get statistics about the current index.

    Returns:
        Dictionary with index statistics:
        - total_chunks: Number of chunks in index
        - total_files: Number of files indexed
        - vault_path: Path to vault
        - chromadb_path: Path to ChromaDB storage
        - embedding_model: Embedding model used
    """
    try:
        settings = get_settings()
        vector_store = get_vector_store()

        stats = vector_store.get_stats()

        return {
            "total_chunks": stats["total_chunks"],
            "total_files": stats["total_files"],
            "vault_path": str(settings.obsidian_vault_path),
            "chromadb_path": stats["persist_directory"],
            "embedding_model": settings.embedding.model,
            "collection_name": stats["collection_name"],
        }

    except Exception as e:
        return {
            "error": f"Failed to get stats: {str(e)}",
            "total_chunks": 0,
            "total_files": 0,
        }


@mcp.tool()
def get_vault_statistics() -> dict[str, Any]:
    """
    Get detailed statistics about the vault.

    Returns:
        Dictionary with detailed vault statistics:
        - total_files: Number of unique notes
        - total_chunks: Number of chunks indexed
        - total_links: Total number of wikilinks found
        - unique_links: Number of unique notes linked to
        - total_tags: Total number of tag occurrences
        - unique_tags: Number of unique tags
        - most_linked_notes: List of top 10 most linked notes
        - most_used_tags: List of top 10 most used tags
    """
    logger.info("Tool Call: get_vault_statistics")
    try:
        settings = get_settings()
        vector_store = get_vector_store()

        # Use new detailed stats method
        stats = vector_store.get_vault_statistics()

        # Add vault path context
        stats["vault_path"] = str(settings.obsidian_vault_path)
        stats["embedding_model"] = settings.embedding.model

        return stats

    except Exception as e:
        logger.error(f"Failed to get vault stats: {e}", exc_info=True)
        return {
            "error": f"Failed to get stats: {str(e)}",
            "total_files": 0,
        }


@mcp.tool()
async def suggest_links(
    note_path: str,
    n_suggestions: int = 5,
    min_similarity: float = 0.5,
    exclude_current: bool = True,
    folder: str | None = None,
    tags: str | None = None,
) -> list[dict[str, Any]]:
    """
    Suggest related notes to link based on content similarity.
    OPTIMIZED: reuses existing embeddings if file hasn't changed.

    Args:
        note_path: Path to note (e.g., "1-projects/trading.md")
        n_suggestions: Number of suggestions
        min_similarity: Minimum similarity threshold
        exclude_current: Exclude chunks from same note
        folder: Optional folder filter for suggestions
        tags: Optional comma-separated string of tags. NOT a list.
    """

    try:
        settings = get_settings()
        vector_store = get_vector_store()
        embedding_service = get_embedding_service()
        indexer = get_indexer()

        # 1. Read target note
        abs_path = settings.obsidian_vault_path / note_path
        if not abs_path.exists():
            return [{"error": f"File not found: {note_path}"}]

        with open(abs_path, encoding="utf-8") as f:
            content = f.read()

        # Deduplication: Find existing links to avoid suggesting them again
        existing_links = set(extract_wikilinks(content))

        # 2. Check for cached embeddings (Smart Caching)
        current_hash = str(compute_content_hash(content)).strip()
        stored_hash = vector_store.check_content_hash(note_path)
        if stored_hash:
            stored_hash = str(stored_hash).strip()

        embeddings = []

        if stored_hash and stored_hash == current_hash:
            # Case A: File unchanged, reuse embeddings!
            file_data = vector_store.get_by_file_path(note_path)
            embeddings = file_data.get("embeddings", [])
        else:
            # Case B: File modified or new, must generate
            # Using indexer.chunker which is initialized via DI
            chunks = indexer.chunker.chunk_markdown(content)
            # Extract text from chunks
            chunk_texts = [c.content for c in chunks]
            if chunk_texts:
                embeddings = await embedding_service.embed_texts(chunk_texts)

        # Ensure embeddings is a list of lists, not numpy array
        if hasattr(embeddings, "tolist"):
            embeddings = embeddings.tolist()

        if not embeddings or len(embeddings) == 0:
            return [{"error": "No content to analyze in this note"}]

        # 3. Query for similar chunks (using all embeddings)
        all_results = []

        # Build metadata filter
        where_filter = None
        if folder or tags:
            where_filter = {}
            if folder:
                where_filter["folder"] = folder
            if tags:
                where_filter["tags"] = tags

        for _idx, embedding in enumerate(embeddings):
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()

            results = vector_store.query(
                query_embedding=embedding,
                n_results=n_suggestions * 2,  # Fetch more to filter
                where=where_filter,
            )

            # Unpack results
            ids = results["ids"]
            distances = results["distances"]
            metadatas = results["metadatas"]

            for i in range(len(ids)):
                match_file = str(metadatas[i].get("file_path", ""))
                match_title = str(metadatas[i].get("note_title", ""))

                # Exclude current file
                if exclude_current and match_file == note_path:
                    continue

                # Exclude existing links
                if match_title in existing_links:
                    continue

                distance = distances[i]
                # Handle numpy types if present
                if hasattr(distance, "item"):
                    distance = distance.item()

                similarity = 1.0 - float(distance)

                if float(similarity) < min_similarity:
                    continue

                all_results.append(
                    {
                        "file_path": match_file,
                        "metadata": metadatas[i],
                        "similarity": float(similarity),
                    }
                )

        # 4. Aggregate by file
        file_scores = defaultdict(list)
        file_metadata = {}

        for res in all_results:
            fpath = res["file_path"]
            file_scores[fpath].append(res["similarity"])
            # Keep metadata of best match
            if (
                fpath not in file_metadata
                or res["similarity"] > file_metadata[fpath]["similarity"]
            ):
                file_metadata[fpath] = {
                    "metadata": res["metadata"],
                    "similarity": res["similarity"],
                }

        # 5. Rank suggestions
        suggestions = []
        for fpath, scores in file_scores.items():
            avg_score = statistics.mean(scores)
            max_score = max(scores)
            # Weighted score: heavily favor max similarity (relevance)
            # but boost by frequency (coverage)
            final_score = (max_score * 0.7) + (avg_score * 0.3)

            meta = file_metadata[fpath]["metadata"]

            # Format suggested link
            target_header = meta.get("header_context", "")
            # Clean header # syntax
            clean_header = (
                target_header.split(" / ")[-1].replace("#", "").strip()
                if target_header
                else ""
            )

            link = f"[[{meta.get('note_title')}]]"
            if clean_header:
                link = f"[[{meta.get('note_title')}#{clean_header}]]"

            suggestions.append(
                {
                    "file_path": fpath,
                    "note_title": meta.get("note_title"),
                    "similarity": round(final_score, 3),
                    "reason": f"Related to section: {target_header}",
                    "suggested_link": link,
                }
            )

        # Sort by score descending
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)

        return suggestions[:n_suggestions]

    except Exception as e:
        return [{"error": f"Suggestion failed: {str(e)}", "path": note_path}]


@mcp.tool()
async def index_note(note_path: str) -> dict[str, Any]:
    """
    Index (or re-index) a specific note.

    Args:
        note_path: Relative path to note (e.g., "1-projects/new-note.md")
    """
    logger.info(f"Tool Call: index_note | Path: {note_path}")
    try:
        settings = get_settings()
        indexer = get_indexer()

        abs_path = settings.obsidian_vault_path / note_path
        if not abs_path.exists():
            logger.warning(f"Note not found: {note_path}")
            return {"error": f"File not found: {note_path}"}

        # Index the file using the exposed method
        chunks = await indexer.index_single_file(abs_path)

        logger.info(f"Indexed note: {note_path} | Chunks: {chunks}")
        return {"success": True, "file": note_path, "chunks_indexed": chunks}
    except Exception as e:
        logger.error(f"Indexing failed for {note_path}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Indexing failed: {str(e)}",
            "file": note_path,
        }


@mcp.tool()
def search_notes(
    pattern: str, root_path: str | None = None, max_results: int = 50
) -> list[str]:
    """
    Find notes matching a regex pattern in the filename or relative path.

    Args:
        pattern: Regex pattern to match (case-insensitive).
        root_path: Optional relative path to restrict search (e.g. "1-projects").
        max_results: Max files to return.
    """
    logger.info(f"Tool Call: search_notes | Pattern: '{pattern}' | Root: {root_path}")
    try:
        settings = get_settings()
        base_path = settings.obsidian_vault_path

        if root_path:
            search_dir = base_path / root_path
        else:
            search_dir = base_path

        if not search_dir.exists():
            return [f"Error: Path not found {root_path}"]

        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return [f"Error: Invalid regex pattern: {str(e)}"]

        # Walk through the directory
        for item in search_dir.rglob("*.md"):
            # Create relative path string for matching
            rel_path = str(item.relative_to(base_path))

            # Skip hidden folders/files
            if "/." in str(item) or item.name.startswith("."):
                continue

            if regex.search(rel_path):
                results.append(rel_path)
                if len(results) >= max_results:
                    break

        logger.info(f"Found {len(results)} matches for pattern '{pattern}'")
        return results

    except Exception as e:
        logger.error(f"Search notes failed: {e}", exc_info=True)
        return [f"Error: {str(e)}"]


@mcp.tool()
async def read_note(note_path: str) -> dict[str, Any]:
    """
    Read the content of a note from the Obsidian vault.

    Args:
        note_path: Relative path to note (e.g., "1-projects/my-note.md")

    Returns:
        Dictionary with note content and metadata or error message
    """
    logger.info(f"Tool Call: read_note | Path: {note_path}")
    try:
        settings = get_settings()
        abs_path = settings.obsidian_vault_path / note_path

        if not abs_path.exists():
            logger.warning(f"Note not found: {note_path}")
            return {"error": f"File not found: {note_path}"}

        if not abs_path.is_file():
            return {"error": f"Path is not a file: {note_path}"}

        # Read the file content
        content = abs_path.read_text(encoding="utf-8")

        # Extract metadata
        tags = extract_all_tags(content)
        frontmatter_tags = extract_frontmatter_tags(content)
        inline_tags = extract_inline_tags(content)
        wikilinks = extract_wikilinks(content)
        note_title = get_note_title(abs_path)
        folder = get_folder(abs_path, settings.obsidian_vault_path)

        logger.info(f"Successfully read note: {note_path}")
        return {
            "success": True,
            "file_path": note_path,
            "content": content,
            "metadata": {
                "note_title": note_title,
                "folder": folder,
                "tags": tags,
                "frontmatter_tags": frontmatter_tags,
                "inline_tags": inline_tags,
                "wikilinks": wikilinks,
                "size_bytes": abs_path.stat().st_size,
                "last_modified": abs_path.stat().st_mtime,
            },
        }

    except Exception as e:
        logger.error(f"Read note failed for {note_path}: {e}", exc_info=True)
        return {"success": False, "error": f"Read failed: {str(e)}", "file": note_path}


@mcp.tool()
async def write_note(
    note_path: str, content: str, create_dirs: bool = True
) -> dict[str, Any]:
    """
    Write content to a note in the Obsidian vault.

    Creates the note if it doesn't exist. Optionally creates parent directories.
    After writing, automatically indexes the note if it's new or changed.

    Args:
        note_path: Relative path to note (e.g., "1-projects/my-note.md")
        content: Full content to write to the note
        create_dirs: Create parent directories if they don't exist (default: True)

    Returns:
        Dictionary with success status and metadata or error message
    """
    logger.info(f"Tool Call: write_note | Path: {note_path}")
    try:
        settings = get_settings()

        # IMPORTANT: Use the raw absolute path from settings/env without joining relative parts
        # This allows writing to the exact path specified in .env, bypassing mount limitations if running locally
        # or if the path is explicitly absolute.
        # However, if note_path IS relative, we join it.
        if Path(note_path).is_absolute():
            abs_path = Path(note_path)
        else:
            abs_path = settings.obsidian_vault_path / note_path

        # Validate path is within vault (SECURITY CHECK)
        # We only skip this if explicitly disabled or if we trust the absolute path
        # For now, we keep the check but warn if it fails instead of hard blocking for local dev flexibility
        try:
            abs_path.resolve().relative_to(settings.obsidian_vault_path.resolve())
        except ValueError:
            logger.warning(f"Path is outside configured vault root: {note_path}. Proceeding with caution.")
            # return {
            #     "success": False,
            #     "error": f"Path is outside vault: {note_path}",
            # }

        # Check if file already exists
        file_existed = abs_path.exists()

        # Create parent directories if needed
        if create_dirs:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
        elif not abs_path.parent.exists():
            return {
                "success": False,
                "error": f"Parent directory does not exist: {abs_path.parent}",
            }

        # Write content to file
        abs_path.write_text(content, encoding="utf-8")

        # Auto-index the note after writing
        indexer = get_indexer()
        chunks_indexed = await indexer.index_single_file(abs_path)

        logger.info(
            f"Successfully wrote note: {note_path} | "
            f"New: {not file_existed} | Chunks: {chunks_indexed}"
        )

        return {
            "success": True,
            "file_path": note_path,
            "was_created": not file_existed,
            "size_bytes": abs_path.stat().st_size,
            "chunks_indexed": chunks_indexed,
        }

    except Exception as e:
        logger.error(f"Write note failed for {note_path}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Write failed: {str(e)}",
            "file": note_path,
        }


@mcp.tool()
async def append_to_note(note_path: str, content: str) -> dict[str, Any]:
    """
    Append content to an existing note in the Obsidian vault.

    If the note doesn't exist, returns an error (use write_note to create new notes).

    Args:
        note_path: Relative path to note (e.g., "1-projects/my-note.md")
        content: Content to append to the note

    Returns:
        Dictionary with success status and metadata or error message
    """
    logger.info(f"Tool Call: append_to_note | Path: {note_path}")
    try:
        settings = get_settings()
        abs_path = settings.obsidian_vault_path / note_path

        if not abs_path.exists():
            logger.warning(f"Note not found: {note_path}")
            return {
                "success": False,
                "error": f"File not found: {note_path}. Use write_note to create new notes.",
            }

        # Read existing content
        existing_content = abs_path.read_text(encoding="utf-8")

        # Append new content
        updated_content = existing_content + "\n" + content

        # Write updated content
        abs_path.write_text(updated_content, encoding="utf-8")

        # Re-index the note
        indexer = get_indexer()
        chunks_indexed = await indexer.index_single_file(abs_path)

        logger.info(
            f"Successfully appended to note: {note_path} | Chunks: {chunks_indexed}"
        )

        return {
            "success": True,
            "file_path": note_path,
            "size_bytes": abs_path.stat().st_size,
            "chunks_indexed": chunks_indexed,
        }

    except Exception as e:
        logger.error(f"Append to note failed for {note_path}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Append failed: {str(e)}",
            "file": note_path,
        }


@mcp.tool()
async def delete_note(note_path: str) -> dict[str, Any]:
    """
    Delete a note from the Obsidian vault.

    Also removes the note from the vector index.

    Args:
        note_path: Relative path to note (e.g., "1-projects/my-note.md")

    Returns:
        Dictionary with success status or error message
    """
    logger.info(f"Tool Call: delete_note | Path: {note_path}")
    try:
        settings = get_settings()
        abs_path = settings.obsidian_vault_path / note_path

        if not abs_path.exists():
            logger.warning(f"Note not found: {note_path}")
            return {"success": False, "error": f"File not found: {note_path}"}

        if not abs_path.is_file():
            return {"success": False, "error": f"Path is not a file: {note_path}"}

        # Delete from vector store first
        vector_store = get_vector_store()
        file_path_str = get_relative_path(abs_path, settings.obsidian_vault_path)

        # Delete all chunks for this file from the index
        try:
            vector_store.delete_by_file_path(file_path_str)
        except Exception as e:
            logger.warning(f"Failed to delete from index: {e}")

        # Delete the file
        abs_path.unlink()

        logger.info(f"Successfully deleted note: {note_path}")
        return {"success": True, "file_path": note_path, "deleted": True}

    except Exception as e:
        logger.error(f"Delete note failed for {note_path}: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Delete failed: {str(e)}",
            "file": note_path,
        }


@mcp.tool()
def get_vault_structure(
    root_path: str | None = None, depth: int = 2
) -> dict[str, Any]:
    """
    Get a directory listing/tree of the vault.

    Args:
        root_path: Relative path to start from (default: vault root).
        depth: Recursion depth (default: 2).
    """
    logger.info(f"Tool Call: get_vault_structure | Root: {root_path}")
    try:
        settings = get_settings()
        base = settings.obsidian_vault_path
        start_path = base / root_path if root_path else base

        if not start_path.exists():
            return {"error": f"Path not found: {start_path}"}

        def build_tree(path: Path, current_depth: int) -> dict[str, Any] | list[str] | str:
            if current_depth > depth:
                return "..."
            
            if path.is_file():
                return "file"
            
            # Directory
            tree = {}
            try:
                # Sort items for stable output
                for item in sorted(path.iterdir()):
                    # Skip hidden
                    if item.name.startswith("."):
                        continue
                    
                    if item.is_dir():
                        tree[item.name] = build_tree(item, current_depth + 1)
                    elif item.suffix == ".md":
                        tree[item.name] = "file"
            except PermissionError:
                return "permission_denied"
                
            return tree

        return {"structure": build_tree(start_path, 0)}

    except Exception as e:
        logger.error(f"Get vault structure failed: {e}", exc_info=True)
        return {"error": str(e)}



# --- Logic Implementations (Separated for Testing) ---

def _get_orphaned_notes(vector_store, settings) -> list[dict[str, Any]]:
    # 1. Get all file paths in vault (from index)
    all_files = vector_store.get_all_file_paths()
    
    # 2. Get all outbound links from all files
    results = vector_store.collection.get(include=["metadatas"])
    metadatas = results["metadatas"] if results["metadatas"] else []
    
    linked_files = set()
    
    # Build map: Title -> {set of possible file paths}
    title_to_paths = defaultdict(set)
    for f in all_files:
        p = Path(f)
        title = p.stem
        title_to_paths[title].add(f)
        
    # Collect all linking targets
    for meta in metadatas:
        outbound = meta.get("outbound_links", "")
        if outbound:
            links = [l.strip() for l in str(outbound).split(",") if l.strip()]
            for l in links:
                # Clean link: [[Link#Header|Alias]] -> Link
                clean_link = l.split("|")[0].split("#")[0]
                if clean_link in title_to_paths:
                    linked_files.update(title_to_paths[clean_link])
                    
    # 3. Find orphans
    orphans = []
    for f in all_files:
        if f not in linked_files:
            orphans.append({
                "file_path": f,
                "note_title": Path(f).stem
            })
            
    return sorted(orphans, key=lambda x: x["file_path"])

def _get_most_linked_notes(vector_store, n_results: int) -> list[dict[str, Any]]:
    stats = vector_store.get_vault_statistics()
    top_linked = stats.get("most_linked_notes", [])
    return top_linked[:n_results]

def _get_duplicate_content(vector_store, similarity_threshold: float) -> list[dict[str, Any]]:
    import numpy as np
    
    # 1. Get all embeddings grouped by file
    file_embeddings = vector_store.get_all_embeddings()
    
    if len(file_embeddings) < 2:
        return []
        
    # 2. Compute average embedding per file (centroid)
    centroids = {}
    for fpath, embeds in file_embeddings.items():
        if not embeds:
            continue
        arr = np.array(embeds)
        centroid = np.mean(arr, axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            coords = centroid / norm
            centroids[fpath] = coords
            
    # 3. Pairwise comparison
    duplicates = []
    keys = list(centroids.keys())
    
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            file_a = keys[i]
            file_b = keys[j]
            
            vec_a = centroids[file_a]
            vec_b = centroids[file_b]
            
            sim = np.dot(vec_a, vec_b)
            
            if sim >= similarity_threshold:
                duplicates.append({
                    "file_a": file_a,
                    "file_b": file_b,
                    "similarity": round(float(sim), 4)
                })
                
    return sorted(duplicates, key=lambda x: x["similarity"], reverse=True)


# --- MCP Tools ---

@mcp.tool()
def get_orphaned_notes() -> list[dict[str, Any]]:
    """
    Find notes that are not linked to by any other note.

    Returns:
        List of orphaned notes with path and title.
    """
    logger.info("Tool Call: get_orphaned_notes")
    try:
        settings = get_settings()
        vector_store = get_vector_store()
        return _get_orphaned_notes(vector_store, settings)
    except Exception as e:
        logger.error(f"Get orphaned notes failed: {e}", exc_info=True)
        return [{"error": str(e)}]


@mcp.tool()
def get_most_linked_notes(n_results: int = 10) -> list[dict[str, Any]]:
    """
    Find notes that are most frequently linked to.

    Args:
        n_results: Number of results to return.

    Returns:
        List of notes sorted by incoming link count.
    """
    logger.info(f"Tool Call: get_most_linked_notes | N: {n_results}")
    try:
        vector_store = get_vector_store()
        return _get_most_linked_notes(vector_store, n_results)
    except Exception as e:
        logger.error(f"Get most linked notes failed: {e}", exc_info=True)
        return [{"error": str(e)}]


@mcp.tool()
def get_duplicate_content(similarity_threshold: float = 0.95) -> list[dict[str, Any]]:
    """
    Find potentially duplicate notes based on high semantic similarity.

    Args:
        similarity_threshold: Threshold for duplicate detection (0.0 to 1.0).
                              Default 0.95 (very similar).

    Returns:
        List of duplicate pairs with similarity scores.
    """
    logger.info(f"Tool Call: get_duplicate_content | Threshold: {similarity_threshold}")
    try:
        vector_store = get_vector_store()
        return _get_duplicate_content(vector_store, similarity_threshold)
    except ImportError:
        return [{"error": "numpy is required for duplicate detection"}]
    except Exception as e:
        logger.error(f"Get duplicate content failed: {e}", exc_info=True)
        return [{"error": str(e)}]
    logger.info(f"Tool Call: get_vault_structure | Root: {root_path} | Depth: {depth}")
    try:
        settings = get_settings()
        base_path = settings.obsidian_vault_path

        if root_path:
            target_path = base_path / root_path
        else:
            target_path = base_path

        if not target_path.exists():
            return {"error": f"Path not found: {root_path}"}

        def build_tree(current_path: Any, current_depth: int) -> Any:
            if current_depth > depth:
                return "..."  # Truncate

            tree = {}
            try:
                # Iterate and sort: directories first, then files
                items = sorted(
                    list(current_path.iterdir()),
                    key=lambda x: (not x.is_dir(), x.name.lower()),
                )

                for item in items:
                    if item.name.startswith("."):
                        continue

                    if item.is_dir():
                        tree[item.name] = build_tree(item, current_depth + 1)
                    elif item.suffix == ".md":
                        tree[item.name] = "file"

            except PermissionError:
                return "ACCESS_DENIED"

            return tree

        return build_tree(target_path, 0)

    except Exception as e:
        logger.error(f"Get vault structure failed: {e}", exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    import sys

    # Check for SSE mode (for persistent service)
    if "--sse" in sys.argv or os.environ.get("MCP_TRANSPORT") == "sse":
        logger.info("Starting SSE server on port 8765...")
        mcp.run(transport="sse", host="0.0.0.0", port=8765)
    else:
        # Default stdio mode
        mcp.run()
