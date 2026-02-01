---
title: Shadow Observer Design
version: 1.2.0
updated: 2026-02-01T02:15:00+01:00
status: implemented
scope: watcher, logging
category: analytics
subcategory: logging
domain: [analytics, watcher, agent]
changelog:
  - 1.2.0 (2026-02-01): Added Git Commit Monitoring feature.
  - 1.1.0 (2026-02-01): Updated to reflect Markdown log format, 1-hour session timeout, and smart upsert logic.
---

# Shadow Observer Design

## Objective
Design a background "Shadow Observer" agent that monitors file changes and chunking activities in the Obsidian vault, generating a structured, machine-readable developer log (`dev-log.md`) in real-time.

## 1. Architecture
We implemented the **Observer Pattern** by extending the existing `VaultWatcher`.

- **`ShadowObserver` Class**: A lightweight, non-blocking class responsible for session tracking and log formatting.
- **`VaultWatcher` Integration**: Modified to accept a list of `observers`. It broadcasts events to these observers immediately after a file is successfully indexed in its background thread.
- **Concurrency**: Logging occurs synchronously within the watcher's existing thread. Using a simple append-only strategy ensures negligible performance impact.
- **Feedback Loop Prevention**: The watcher explicitly ignores `dev-log.md` and `shadow-debug.log` to prevent infinite indexing loops.
- **Git Monitoring**: The watcher monitors `.git/logs/HEAD` to detect new commits without requiring client-side hooks.

## 2. Log Schema (`dev-log.md`)
The log utilizes a structured **Markdown** format with AI-generated summaries.

**Format Example (File Edit):**
```markdown
# Developer Log

## [2026-02-01]

### Session `sess_4f9e2559`
- **01:43:05**: Modified [[1-projects/unitai-omni/omni-search-engine/docs.md]] (6 chunks, 5 edits over 2m 30s)
  > **AI Analysis**: The change adds a new requirement for precise filtering of indexed files to exclude non-note content.
```

**Format Example (Git Commit):**
```markdown
  <entry id="evt_commit_a1b2c3d" timestamp="2026-02-01T02:15:00" type="commit">
    <source>git</source>
    <commit_hash>a1b2c3d</commit_hash>
    <author>Jane Doe</author>
    <message>feat: add new logging feature</message>
    <summary>Implemented git commit monitoring in ShadowObserver.</summary>
  </entry>
```

**Key Features:**
- **Consolidation**: Multiple edits to the same file within a session are updated in-place (rewriting the last line) to reduce noise.
- **AI Upserting**: AI analysis summaries are inserted or updated for the relevant file entry, ensuring only the most recent insight is shown.
- **Commit Logging**: Commits are logged as distinct entries with metadata and AI analysis of the diff.

## 3. Session Logic
To intelligently group events, we track "Active Sessions" in memory.

- **Session Timeout**: `3600 seconds` (1 hour).
- **Logic**:
    1.  **Check Cache**: Look up the file path in `active_sessions`.
    2.  **Evaluate**:
        -   If `(Current Time - Last Event Time) < 1 hour`: **Continue Session**. Update the existing entry stats (edit count, duration).
        -   Otherwise: **Start New Session**. Generate a new `session_id` and log a `session_start` event.
    3.  **Update**: Update the `Last Event Time` for the file.

## 4. Implementation Details
- **Debouncing**: AI analysis is triggered only after a debounce period (default: `WATCHER_AI_DEBOUNCE_SECONDS` * 2) or on the first significant edit.
- **State Tracking**: `ShadowObserver` tracks `last_ai_time` per session/file to avoid redundant API calls.
- **Git Integration**: `VaultWatcher` specifically whitelists `.git/logs/HEAD` events to trigger `ShadowObserver.on_commit()`.
