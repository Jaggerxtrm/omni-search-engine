"""
Vault Watcher Module

Monitors the Obsidian vault for changes and automatically triggers indexing updates.
Uses the watchdog library for efficient file system monitoring.
"""

import time
import threading
from pathlib import Path
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from services.indexer_service import VaultIndexer
from repositories.snippet_repository import VectorStore
from utils import get_relative_path
from logger import get_logger

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
        debounce_seconds: float = 30.0
    ):
        self.vault_path = vault_path
        self.indexer = indexer
        self.vector_store = vector_store
        self.debounce_seconds = debounce_seconds
        
        # Coalescing state
        self._pending_files: Dict[str, float] = {}  # path -> execution_deadline
        self._lock = threading.Lock()
        self._running = False
        self._ticker_thread = None
        
        self.observer = Observer()

    def start(self):
        """Start monitoring the vault."""
        logger.info(f"Starting Vault Watcher (Coalescing Debounce: {self.debounce_seconds}s)")
        
        # Start ticker thread
        self._running = True
        self._ticker_thread = threading.Thread(target=self._process_pending, daemon=True)
        self._ticker_thread.start()
        
        self.observer.schedule(self, str(self.vault_path), recursive=True)
        self.observer.start()

    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        if self._ticker_thread:
            self._ticker_thread.join(timeout=1.0)

    def _process_pending(self):
        """Background loop to process debounced events."""
        while self._running:
            now = time.time()
            to_process = []
            
            with self._lock:
                # Find expired deadlines
                for path, deadline in list(self._pending_files.items()):
                    if now >= deadline:
                        to_process.append(path)
                        del self._pending_files[path]
            
            # Process files outside lock
            for path_str in to_process:
                path = Path(path_str)
                if not path.exists():
                     # Check if it was deleted (handled by on_deleted immediately usually)
                     # But for safety:
                     continue
                     
                logger.info(f"Debounce expired, processing: {path.name}")
                try:
                    self.indexer.index_single_file(path)
                except Exception as e:
                    logger.error(f"Failed to index {path.name}: {e}")

            time.sleep(1.0) # Check every second

    def _coalesce_event(self, file_path: Path):
        """Schedule file for processing after debounce delay."""
        # Only process .md files
        if file_path.suffix != '.md':
            return
        # Ignore hidden info
        if any(part.startswith('.') for part in file_path.parts):
            return

        with self._lock:
            deadline = time.time() + self.debounce_seconds
            self._pending_files[str(file_path)] = deadline
            logger.debug(f"Scheduled {file_path.name} in {self.debounce_seconds}s")

    def on_created(self, event: FileSystemEvent):
        if event.is_directory: return
        self._coalesce_event(Path(event.src_path))

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory: return
        self._coalesce_event(Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory: return
        path = Path(event.src_path)
        if path.suffix != '.md': return

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

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory: return
        src = Path(event.src_path)
        dest = Path(event.dest_path)
        
        # Treat move as: delete src (immediate) + create dest (coalesced)
        if src.suffix == '.md':
             # ... (Keep existing optimized move logic? Or just coalesce?)
             # Optimized move is better than re-index. Let's try to keep it immediate.
             pass
             
        # Actually for simplicity and robustness with atomic saves (which often look like move tmp->target),
        # we should probably just treat it as a modification of target.
        # BUT atomic save is often: write tmp, move tmp -> target.
        # watcher sees: create tmp, modify tmp, move tmp->target.
        
        if dest.suffix == '.md':
             self._coalesce_event(dest)
