# Shadow Observer Design

## Objective
Design a background "Shadow Observer" agent that monitors file changes and chunking activities in the Obsidian vault, generating a structured, machine-readable developer log (`dev-log.md`) in real-time.

## 1. Architecture
We will implement the **Observer Pattern** by extending the existing `VaultWatcher`.

- **`ShadowObserver` Class**: A lightweight, non-blocking class responsible for session tracking and log formatting.
- **`VaultWatcher` Integration**: Modified to accept a list of `observers`. It broadcasts events to these observers immediately after a file is successfully indexed in its background thread.
- **Concurrency**: Logging occurs synchronously within the watcher's existing thread. Using a simple append-only strategy ensures negligible performance impact.

## 2. Log Schema (`dev-log.md`)
The log utilizes a **Hybrid Markdown/XML** format. This provides human readability while ensuring strict machine parsability for future agents.

**Format Example:**
```xml
# Developer Log

<log>
  <!-- New Session Detected -->
  <entry id="evt_1706521200" timestamp="2026-01-29T10:00:00.123" session_id="sess_a1b2c3d4" type="session_start">
    <file>notes/architecture.md</file>
    <source>vault</source>
    <context>New session (previous activity > 5m ago)</context>
  </entry>

  <!-- Ongoing Edits -->
  <entry id="evt_1706521230" timestamp="2026-01-29T10:00:30.456" session_id="sess_a1b2c3d4" type="modification">
    <file>notes/architecture.md</file>
    <source>vault</source>
    <stats>
      <chunks_generated>5</chunks_generated>
      <processing_time_ms>120</processing_time_ms>
    </stats>
  </entry>
</log>
```

## 3. Session Logic
To intelligently group events, we track "Active Sessions" in memory.

- **Session Timeout**: `300 seconds` (5 minutes).
- **Logic**:
    1.  **Check Cache**: Look up the file path in `active_sessions`.
    2.  **Evaluate**:
        -   If `(Current Time - Last Event Time) < 5 minutes`: **Continue Session**. Log a `modification` event using the existing `session_id`.
        -   Otherwise: **Start New Session**. Generate a new `session_id` and log a `session_start` event.
    3.  **Update**: Update the `Last Event Time` for the file.

## 4. Implementation Steps
1.  **Modify `watcher.py`**:
    -   Add `ShadowObserver` class with session tracking and XML generation logic.
    -   Update `VaultWatcher` to accept and notify observers.
2.  **Update `server.py`**:
    -   Instantiate `ShadowObserver` in the `lifespan` function.
    -   Register it with the `VaultWatcher` instance.
