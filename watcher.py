"""
Vault Watcher Module

Monitors the Obsidian vault for changes and automatically triggers indexing updates.
Uses the watchdog library for efficient file system monitoring.
"""

import asyncio
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from logger import get_logger
from repositories.snippet_repository import VectorStore
from services.indexer_service import VaultIndexer
from utils import get_relative_path

logger = get_logger("watcher")


class VaultWatcher(FileSystemEventHandler):
    """
    Handles file system events for the Obsidian vault and triggers indexing updates.
    """

    def __init__(
        self,
        vault_path: Path,
        indexer: VaultIndexer,
        vector_store: VectorStore,
        debounce_seconds: float = 30.0,
    ):
        self.vault_path = vault_path
        self.indexer = indexer
        self.vector_store = vector_store
        self.debounce_seconds = debounce_seconds

        # Coalescing state
        self._pending_files: dict[str, float] = {}  # path -> execution_deadline
        self._lock = threading.Lock()
        self._running = False
        self._ticker_thread: threading.Thread | None = None

        self.observer = Observer()

    def start(self) -> None:
        """Start monitoring the vault."""
        logger.info(
            f"Starting Vault Watcher (Coalescing Debounce: {self.debounce_seconds}s)"
        )

        # Start ticker thread
        self._running = True
        self._ticker_thread = threading.Thread(
            target=self._process_pending, daemon=True
        )
        self._ticker_thread.start()

        self.observer.schedule(self, str(self.vault_path), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        if self._ticker_thread:
            self._ticker_thread.join(timeout=1.0)

    def _process_pending(self) -> None:
        """Background loop to process debounced events."""
        while self._running:
            now = time.time()
            to_process = []

            with self._lock:
                # Find expired deadlines
                for p, deadline in list(self._pending_files.items()):
                    if now >= deadline:
                        to_process.append(p)
                        del self._pending_files[p]

            # Process files outside lock
            for path_str in to_process:
                path = Path(path_str)
                if not path.exists():
                    # Check if it was deleted (handled by on_deleted immediately usually)
                    # But for safety:
                    continue

                logger.info(f"Debounce expired, processing: {path.name}")
                try:
                    chunks = asyncio.run(self.indexer.index_single_file(path))
                    logger.info(f"Successfully processed {path.name} ({chunks} chunks)")
                except Exception as e:
                    logger.error(f"Failed to index {path.name}: {e}")

            time.sleep(1.0)  # Check every second

    def _coalesce_event(self, file_path: Path) -> None:
        """Schedule file for processing after debounce delay."""
        # Only process .md files
        if file_path.suffix != ".md":
            return
        # Ignore hidden info
        if any(part.startswith(".") for part in file_path.parts):
            return

        with self._lock:
            deadline = time.time() + self.debounce_seconds
            self._pending_files[str(file_path)] = deadline
            logger.debug(f"Scheduled {file_path.name} in {self.debounce_seconds}s")

    def _get_path(self, event: FileSystemEvent) -> Path:
        """Helper to safely get Path from event src_path."""
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        return Path(src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._coalesce_event(self._get_path(event))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._coalesce_event(self._get_path(event))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = self._get_path(event)
        if path.suffix != ".md":
            return

        # Deletions are immediate, cancel any pending index
        with self._lock:
            if str(path) in self._pending_files:
                del self._pending_files[str(path)]

        logger.info(f"File deleted: {path.name}")
        try:
            rel_path = get_relative_path(path, self.vault_path)
            self.vector_store.delete_by_file_path(rel_path)
        except Exception as e:
            logger.error(f"Failed to delete embeddings for {path}: {e}")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        # 1. Handle deletion of source file (source path)
        src_path = self._get_path(event) # Note: _get_path uses event.src_path
        if src_path.suffix == ".md":
             # We treat move as delete + create for robustness
            with self._lock:
                if str(src_path) in self._pending_files:
                    del self._pending_files[str(src_path)]
            
            logger.info(f"File moved (source): {src_path.name}")
            try:
                rel_path = get_relative_path(src_path, self.vault_path)
                self.vector_store.delete_by_file_path(rel_path)
            except Exception as e:
                logger.error(f"Failed to delete embeddings for moved source {src_path}: {e}")

        # 2. Handle creation of destination file
        dest_path = event.dest_path
        if isinstance(dest_path, bytes):
            dest_path = dest_path.decode("utf-8")
        dest = Path(dest_path)

        if dest.suffix == ".md":
            self._coalesce_event(dest)
