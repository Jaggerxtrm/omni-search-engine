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
from qwen_credential import QwenWrapper

logger = get_logger("watcher")

from settings import SourceConfig, get_settings

class ShadowObserver:
    """
    Background observer that logs file activities to a structured dev-log.md.
    Uses Qwen AI to summarize changes after a debounce period.
    Also monitors Git commits to log development progress.
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
        self.session_timeout_seconds = 300  # 5 minutes as per design

        self._lock = threading.Lock()

        # Async Executor for AI/Git tasks
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ShadowAI")

        # State for log formatting
        self.last_logged_session_id = None
        self.last_logged_file_path = None

        # Qwen wrapper with credential rotation
        self.qwen_wrapper = QwenWrapper(max_retries=5)

        self._ensure_log_header()

    def _ensure_log_header(self):
        """Ensures the log file exists with a valid header and root tag."""
        if not self.log_path.exists():
            try:
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.write("# Developer Log\n\n<log>\n</log>\n")
            except Exception as e:
                logger.error(f"ShadowObserver: Failed to create log file: {e}")

    def on_file_processed(self, file_path: Path, chunks_count: int, source_id: str):
        """
        Called by VaultWatcher when a file is successfully indexed.
        
        NOTE: Logging of individual file events is DISABLED to reduce noise.
        We only track activity internally if needed, but for now we rely purely on 
        git commits for the developer log.
        """
        pass

    def _process_commit(self, git_dir: Path):
        """Analyze and log the latest commit with a personal assistant style summary."""
        try:
            # Resolve repo root
            if ".git" in str(git_dir):
                repo_root = git_dir.parent.parent.parent
            else:
                repo_root = self.vault_path

            # 1. Get Commit Info
            cmd = ["git", "log", "-1", "--pretty=format:%h|%s|%an|%ai"]
            result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                logger.error(f"Failed to get commit info: {result.stderr}")
                return

            commit_info = result.stdout.strip().split("|")
            if len(commit_info) < 4: return

            short_hash, subject, author, date_iso = commit_info
            
            # 2. Get Commit Diff & Stat
            # We want the stats to see which files changed, and the diff for context
            diff_cmd = ["git", "show", short_hash, "--stat", "--patch"]
            diff_result = subprocess.run(diff_cmd, cwd=repo_root, capture_output=True, text=True, timeout=10)
            diff_text = diff_result.stdout[:6000] # Increased context for better summary

            # 3. AI Analysis - Personal Assistant Persona
            prompt = (
                f"You are a helpful personal assistant for a software developer.\n"
                f"The developer just made a commit with the message: '{subject}'.\n\n"
                f"Here is the diff of their work:\n{diff_text}\n\n"
                f"Please write a brief, friendly session summary (2-3 sentences). \n"
                f"1. Identify the key files they worked on.\n"
                f"2. Explain *what* they achieved in plain English (narrative style).\n"
                f"3. Do not be overly technical; focus on the *intent* and *outcome* of the session.\n"
                f"Example: 'You focused on the authentication module today, specifically updating the login logic in `auth.py`. It looks like you successfully refactored the token generation to be more secure.'"
            )

            qwen_result = self.qwen_wrapper.call_with_fallback(
                prompt,
                fallback_message="Could not generate summary.",
                timeout=45
            )
            ai_analysis = qwen_result

            # 4. Log Entry
            now = time.time()
            timestamp = datetime.datetime.fromtimestamp(now).isoformat()
            event_id = f"evt_commit_{short_hash}"
            
            entry_xml = (
                f'  <entry id="{event_id}" timestamp="{timestamp}" type="session_summary">\n'
                f'    <commit_hash>{short_hash}</commit_hash>\n'
                f'    <message>{subject}</message>\n'
                f'    <assistant_summary>\n'
                f'      {ai_analysis}\n'
                f'    </assistant_summary>\n'
                f'  </entry>'
            )

            with self._lock:
                self._append_to_log_root(entry_xml)

            logger.info(f"Logged session summary for commit {short_hash}")

        except Exception as e:
            logger.error(f"ShadowObserver: Commit processing failed: {e}")

    def _append_to_log_root(self, entry_xml: str):
        """Append an entry before the closing </log> tag."""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if "</log>" in content:
                new_content = content.replace("</log>", f"{entry_xml}\n</log>")
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
            else:
                # Fallback: append
                self._append_log(entry_xml)
        except Exception as e:
            logger.error(f"ShadowObserver: Append to root failed: {e}")

    def _update_last_entry(self, new_entry_xml: str):
        """Replace the last <entry> in the log with an updated version."""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Find the start of the last <entry
            last_entry_start = None
            for i in range(len(lines) - 1, -1, -1):
                if '<entry' in lines[i]:
                    last_entry_start = i
                    break
            
            if last_entry_start is not None:
                # Find the end of this entry
                last_entry_end = None
                for i in range(last_entry_start, len(lines)):
                    if '</entry>' in lines[i]:
                        last_entry_end = i
                        break
                
                if last_entry_end is not None:
                    # Replace the lines
                    del lines[last_entry_start:last_entry_end + 1]
                    lines.insert(last_entry_start, new_entry_xml + "\n")
                    
                    with open(self.log_path, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                else:
                    self._append_to_log_root(new_entry_xml)
            else:
                self._append_to_log_root(new_entry_xml)
        except Exception as e:
            logger.error(f"ShadowObserver: Update last entry failed: {e}")

    def _upsert_ai_analysis(self, summary: str):
        """Insert or replace the <summary> tag inside the last <entry>."""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Find last <entry
            last_entry_start = None
            for i in range(len(lines) - 1, -1, -1):
                if '<entry' in lines[i]:
                    last_entry_start = i
                    break
            
            if last_entry_start is None: return

            # Find end of this entry
            last_entry_end = None
            for i in range(last_entry_start, len(lines)):
                if '</entry>' in lines[i]:
                    last_entry_end = i
                    break
            
            if last_entry_end is None: return

            # Look for existing <summary>
            summary_tag = f'    <summary>{summary}</summary>\n'
            existing_summary_idx = None
            for i in range(last_entry_start, last_entry_end):
                if '<summary>' in lines[i]:
                    existing_summary_idx = i
                    break
            
            if existing_summary_idx is not None:
                lines[existing_summary_idx] = summary_tag
            else:
                # Insert before </entry>
                lines.insert(last_entry_end, summary_tag)

            with open(self.log_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        except Exception as e:
            logger.error(f"ShadowObserver: Upsert AI analysis failed: {e}")

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
        try:
            # Use relative path for git commands to avoid CWD issues
            try:
                rel_path = file_path.relative_to(self.vault_path)
            except ValueError:
                rel_path = file_path.name # Fallback

            diff_output = ""
            is_untracked = False
            
            # 1. Check if file is tracked
            try:
                subprocess.run(
                    ["git", "ls-files", "--error-unmatch", str(rel_path)],
                    cwd=self.vault_path, check=True, capture_output=True, timeout=5
                )
            except subprocess.CalledProcessError:
                is_untracked = True

            # 2. Get Context
            if is_untracked:
                try:
                    content = file_path.read_text(encoding='utf-8')
                    diff_output = f"New Untracked File Content:\n{content[:4000]}"
                except Exception:
                    pass
            else:
                try:
                    cmd = ["git", "diff", "HEAD", "--", str(rel_path)]
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.vault_path, timeout=10)
                    diff_output = result.stdout.strip()
                except Exception:
                    pass

            if not diff_output: return

            # 3. Call Qwen
            prompt = (
                f"Analyze the changes in '{file_path.name}' and provide a concise, single-sentence summary "
                f"suitable for a developer log entry. Focus on intent and key change. "
                f"Diff:\n{diff_output[:4000]}"
            )
            summary = self.qwen_wrapper.call_with_fallback(
                prompt,
                fallback_message="Analysis failed",
                timeout=30
            )

            # Upsert Summary
            with self._lock:
                key = str(file_path)
                if key in self.active_sessions:
                    self.active_sessions[key]['last_ai_time'] = time.time()
                self._upsert_ai_analysis(summary)

        except Exception as e:
            logger.error(f"AI Analysis failed for {file_path}: {e}")

    def _append_log(self, entry: str):
        try:
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

                # Special handling for Git Commits
                if path.name == "HEAD" and ".git/logs" in str(path):
                    logger.info("Detected Git Commit")
                    for obs in self.observers:
                         if hasattr(obs, 'on_commit'):
                             obs.on_commit(path)
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
        
        # Special case: Monitor git commits
        # Check if the path ends with .git/logs/HEAD
        is_commit_log = file_path.name == "HEAD" and ".git/logs" in str(file_path)

        if not is_commit_log:
            # Filter supported extensions (aligned with indexer)
            if file_path.suffix not in ['.md', '.txt', '.py', '.js', '.ts', '.json', '.yaml']:
                return
            
            # Ignore hidden info
            if any(part.startswith(".") for part in file_path.parts):
                return

            # Ignore log files to prevent feedback loops
            if file_path.name in ["dev-log.md", "shadow-debug.log"]:
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
