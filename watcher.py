"""
Vault Watcher Module

Monitors the Obsidian vault for changes and automatically triggers indexing updates.
Uses the watchdog library for efficient file system monitoring.
"""

import asyncio
import threading
import time
import datetime
import uuid
import subprocess
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from logger import get_logger
from repositories.snippet_repository import VectorStore
from services.indexer_service import VaultIndexer
from utils import get_relative_path

logger = get_logger("watcher")

from settings import SourceConfig, get_settings

class ShadowObserver:
    """
    Background observer that logs file activities to a structured dev-log.md.
    Uses Qwen AI to summarize changes after a debounce period.
    """
    def __init__(self, vault_path: Path, log_file: str = "dev-log.md"):
        settings = get_settings()
        self.vault_path = vault_path
        # Resolve to absolute path for safe comparison
        self.log_path = (vault_path / log_file).resolve()
        self.active_sessions = {}
        self.pending_ai_tasks = {}
        
        # Externalized config
        self.ai_debounce_seconds = settings.watcher.ai_debounce_seconds
        
        self._lock = threading.Lock()
        
        # Async Executor for AI/Git tasks
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ShadowAI")

        # State for log formatting
        self.last_logged_date = None
        self.last_logged_session_id = None

        self._ensure_log_header()

    def _ensure_log_header(self):
        """Ensures the log file exists with a valid header."""
        if not self.log_path.exists():
            try:
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.write("# Developer Log\n\n")
            except Exception as e:
                logger.error(f"ShadowObserver: Failed to create log file: {e}")

    def on_file_processed(self, file_path: Path, chunks_count: int, source_id: str):
        """Called by VaultWatcher when a file is successfully indexed."""
        # Prevent infinite loop: do not process the log file itself
        try:
            resolved_file = file_path.resolve()
            # DEBUG LOGGING (Temporary)
            # logger.info(f"ShadowObserver Check: {resolved_file} vs {self.log_path}")
            
            if resolved_file == self.log_path or file_path.name == self.log_path.name:
                logger.info(f"ShadowObserver: Skipping log file {file_path.name}")
                return
        except OSError:
            pass # File might be gone

        with self._lock:
            now = time.time()
            key = str(file_path)
            dt_object = datetime.datetime.fromtimestamp(now)
            date_str = dt_object.strftime("%Y-%m-%d")
            time_str = dt_object.strftime("%H:%M:%S")

            # 1. Update Session State
            session = self.active_sessions.get(key)
            if not session or (now - session['last_event'] > 300):
                session_id = f"sess_{uuid.uuid4().hex[:8]}"
                self.active_sessions[key] = {
                    'start_time': now,
                    'last_event': now,
                    'session_id': session_id
                }
                context_msg = "New session started"
            else:
                session['last_event'] = now
                session_id = session['session_id']
                context_msg = ""

            # 2. Build Markdown Entry
            log_buffer = []

            # Date Header
            if self.last_logged_date != date_str:
                log_buffer.append(f"\n## [{date_str}]")
                self.last_logged_date = date_str
                self.last_logged_session_id = None

            # Session Header
            if self.last_logged_session_id != session_id:
                log_buffer.append(f"\n### Session `{session_id}`")
                self.last_logged_session_id = session_id

            # File Entry
            try:
                rel_path = file_path.relative_to(self.vault_path)
            except ValueError:
                rel_path = file_path.name
            
            entry_line = f"- **{time_str}**: Modified [[{rel_path}]] ({chunks_count} chunks)"
            if context_msg:
                entry_line += f" - *{context_msg}*"
            
            log_buffer.append(entry_line)

            self._append_log("\n".join(log_buffer))

            # 3. Schedule AI Analysis
            self.pending_ai_tasks[key] = now

    def tick(self):
        """Called periodically to check for pending AI tasks."""
        now = time.time()
        to_process = []
        
        with self._lock:
            # Check for expired debounce
            for key, last_time in list(self.pending_ai_tasks.items()):
                if now - last_time >= self.ai_debounce_seconds:
                    to_process.append(Path(key))
                    del self.pending_ai_tasks[key]
        
        # Submit to executor instead of running inline (NON-BLOCKING)
        for file_path in to_process:
            self._executor.submit(self._run_ai_analysis, file_path)

    def _run_ai_analysis(self, file_path: Path):
        """Runs Qwen to analyze changes (Thread-Safe)."""
        debug_log = self.vault_path / "shadow-debug.log"
        
        def log_debug(msg):
            try:
                with open(debug_log, "a", encoding="utf-8") as dbg:
                    dbg.write(f"[{datetime.datetime.now()}] {msg}\n")
            except Exception:
                pass

        log_debug(f"Analyzing {file_path}")

        try:
            diff_output = ""
            is_untracked = False
            
            # Use relative path for git commands to avoid CWD issues
            try:
                rel_path = file_path.relative_to(self.vault_path)
            except ValueError:
                rel_path = file_path.name # Fallback

            # 1. Check if file is tracked
            try:
                # git ls-files --error-unmatch <file> returns 0 if tracked, 1 if not
                subprocess.run(
                    ["git", "ls-files", "--error-unmatch", str(rel_path)],
                    cwd=self.vault_path,
                    check=True,
                    capture_output=True,
                    timeout=5
                )
            except subprocess.CalledProcessError:
                is_untracked = True
            except Exception as e:
                log_debug(f"Git tracking check failed: {e}")
                # Assume tracked or broken git, try diff anyway

            # 2. Get Context (Diff or Full Content)
            if is_untracked:
                try:
                    # Treat new files as full content
                    content = file_path.read_text(encoding='utf-8')
                    # Limit content size for prompt
                    diff_output = f"New Untracked File Content:\n{content[:4000]}"
                except Exception as e:
                    log_debug(f"Failed to read untracked file: {e}")
            else:
                # Standard Git Diff
                try:
                    # Check if HEAD exists (repo might be empty)
                    subprocess.run(
                        ["git", "rev-parse", "HEAD"], 
                        cwd=self.vault_path, 
                        check=True, 
                        capture_output=True,
                        timeout=5
                    )
                    
                    cmd = ["git", "diff", "HEAD", "--", str(rel_path)]
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        cwd=self.vault_path,
                        timeout=10 
                    )
                    if result.returncode == 0:
                        diff_output = result.stdout.strip()
                    else:
                        log_debug(f"Git diff failed: {result.stderr}")
                except subprocess.SubprocessError:
                     # Fallback for empty repo or git error
                     if file_path.exists():
                         try:
                             diff_output = f"File Snapshot (Git failed):\n{file_path.read_text(encoding='utf-8')[:4000]}"
                         except Exception:
                             pass

            if not diff_output:
                return

            # 3. Call Qwen
            prompt = (
                f"Analyze the changes in '{file_path.name}' and provide a concise, single-sentence summary "
                f"suitable for a developer log. Focus on the intent (why) and the key change (what). "
                f"Do not use markdown headers. Diff:\n{diff_output[:4000]}"
            )
            qwen_cmd = ["qwen", prompt, "--output-format", "text"]
            
            qwen_result = subprocess.run(qwen_cmd, capture_output=True, text=True, timeout=30)
            summary = qwen_result.stdout.strip() if qwen_result.returncode == 0 else "Analysis failed"

            # Log AI Entry (Markdown)
            with self._lock:
                ai_entry = f"  > **AI Analysis**: {summary}"
                self._append_log(ai_entry)

        except Exception as e:
            logger.error(f"AI Analysis failed for {file_path}: {e}")
            log_debug(f"EXCEPTION in thread: {e}")

    def _append_log(self, entry: str):
        try:
            # Assumes lock is held by caller if needed, but 'a' is usually safe for appending lines
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception as e:
            logger.error(f"ShadowObserver: Write failed: {e}")


class VaultWatcher(FileSystemEventHandler):
    """
    Handles file system events for all configured sources and triggers indexing updates.
    """

    def __init__(
        self,
        sources: list[SourceConfig],
        indexer: VaultIndexer,
        vector_store: VectorStore,
        debounce_seconds: float = None, # Allow override or default
        observers: list = None,
    ):
        settings = get_settings()
        self.sources = sources
        self.indexer = indexer
        self.vector_store = vector_store
        # Use settings or override
        self.debounce_seconds = debounce_seconds if debounce_seconds is not None else settings.watcher.debounce_seconds
        self.observers = observers or []

        # Coalescing state
        self._pending_files: dict[str, float] = {}  # path -> execution_deadline
        self._lock = threading.Lock()
        self._running = False
        self._ticker_thread: threading.Thread | None = None

        self.observer = Observer()

    def start(self) -> None:
        """Start monitoring all sources."""
        logger.info(
            f"Starting Vault Watcher for {len(self.sources)} sources (Debounce: {self.debounce_seconds}s)"
        )

        # Start ticker thread
        self._running = True
        self._ticker_thread = threading.Thread(
            target=self._process_pending, daemon=True
        )
        self._ticker_thread.start()

        for source in self.sources:
            if source.path.exists():
                logger.info(f"Watching source: {source.id} ({source.path})")
                self.observer.schedule(self, str(source.path), recursive=True)
            else:
                logger.warning(f"Skipping missing source path: {source.path}")
                
        self.observer.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        if self._ticker_thread:
            self._ticker_thread.join(timeout=1.0)

    def _get_source_for_path(self, file_path: Path) -> SourceConfig | None:
        """Resolve which source a file belongs to."""
        # Check explicit sources
        # We process longer paths first to handle nested sources correctly (e.g. repo inside vault?)
        # though that is rare.
        # Simple inclusion check.
        try:
             abs_path = file_path.resolve()
        except OSError:
             return None

        # Helper to check if path is inside root
        def is_relative_to(path, root):
            try:
                path.relative_to(root)
                return True
            except ValueError:
                return False

        for source in self.sources:
            if is_relative_to(abs_path, source.path.resolve()):
                return source
        return None

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

                source = self._get_source_for_path(path)
                if not source:
                    logger.warning(f"Could not resolve source for {path}. Skipping.")
                    continue

                logger.info(f"Debounce expired, processing: {path.name} (Source: {source.id})")
                try:
                    chunks = asyncio.run(
                        self.indexer.index_single_file(path, source.path, source.id)
                    )
                    logger.info(f"Successfully processed {path.name} ({chunks} chunks)")
                    
                    # Notify observers
                    for obs in self.observers:
                        try:
                            obs.on_file_processed(path, chunks, source.id)
                        except Exception as e:
                            logger.error(f"Observer on_file_processed failed: {e}")
                            
                except Exception as e:
                    logger.error(f"Failed to index {path.name}: {e}")

            # Tick observers
            for obs in self.observers:
                if hasattr(obs, 'tick'):
                    try:
                        obs.tick()
                    except Exception as e:
                        logger.error(f"Observer tick failed: {e}")

            time.sleep(1.0)  # Check every second

    def _coalesce_event(self, file_path: Path) -> None:
        """Schedule file for processing after debounce delay."""
        # Filter supported extensions (aligned with indexer)
        if file_path.suffix not in ['.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml']:
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
        
        # Check extension support
        if path.suffix not in ['.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml']:
            return

        # Deletions are immediate, cancel any pending index
        with self._lock:
            if str(path) in self._pending_files:
                del self._pending_files[str(path)]

        source = self._get_source_for_path(path)
        if not source:
             # If file is deleted, we might validly not find it on disk to resolve path?
             # _get_source_for_path uses resolved paths.
             # If file is gone, resolve() might fail or resolve to something else? 
             # Wait, resolve() on non-existing file usually works if parent exists (on Linux).
             # But if not, we can fall back to string matching against source roots.
             
             # Fallback: String matching
             str_path = str(path.absolute())
             for s in self.sources:
                 if str_path.startswith(str(s.path.absolute())):
                     source = s
                     break
        
        if not source:
            logger.warning(f"Could not resolve source for deleted file {path}")
            return

        logger.info(f"File deleted: {path.name} from {source.id}")
        try:
            rel_path = get_relative_path(path, source.path)
            self.vector_store.delete_by_file_path(rel_path, source.id)
        except Exception as e:
            logger.error(f"Failed to delete embeddings for {path}: {e}")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        # 1. Handle deletion of source file (source path)
        src_path = self._get_path(event) # Note: _get_path uses event.src_path
        
        if src_path.suffix in ['.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml']:
             # We treat move as delete + create for robustness
            with self._lock:
                if str(src_path) in self._pending_files:
                    del self._pending_files[str(src_path)]
            
            logger.info(f"File moved (source): {src_path.name}")
            
            # Find source for src_path
            src_source = None
            str_path = str(src_path.absolute())
            for s in self.sources:
                 if str_path.startswith(str(s.path.absolute())):
                     src_source = s
                     break

            if src_source:
                try:
                    rel_path = get_relative_path(src_path, src_source.path)
                    self.vector_store.delete_by_file_path(rel_path, src_source.id)
                except Exception as e:
                    logger.error(f"Failed to delete embeddings for moved source {src_path}: {e}")

        # 2. Handle creation of destination file
        dest_path = event.dest_path
        if isinstance(dest_path, bytes):
            dest_path = dest_path.decode("utf-8")
        dest = Path(dest_path)

        # Trigger create logic if extension supported
        self._coalesce_event(dest)
