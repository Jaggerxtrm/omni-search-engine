---
title: Shadow Observer Design
version: 2.0.0
updated: 2026-02-01T02:30:00+01:00
status: implemented
scope: watcher, logging
category: analytics
subcategory: logging
domain: [analytics, watcher, agent]
changelog:
  - 2.0.0 (2026-02-01): Major refactor to "Commit-Only" workflow. Disabled file modification logs; agent now acts as a personal assistant summarizing sessions upon git commits.
  - 1.2.0 (2026-02-01): Added Git Commit Monitoring feature.
  - 1.1.0 (2026-02-01): Updated to reflect Markdown log format, 1-hour session timeout, and smart upsert logic.
---

# Shadow Observer Design

## Objective
Design a background "Shadow Observer" agent that acts as a personal assistant, generating high-quality summaries of development sessions in `dev-log.md`.

## 1. Architecture (Commit-Only Workflow)
The observer has been simplified to reduce noise and focus on meaningful milestones.

- **Trigger**: The agent wakes up **ONLY** when a git commit is detected (monitoring `.git/logs/HEAD`).
- **File Watching**: While `VaultWatcher` still indexes files for search in real-time, `ShadowObserver` **ignores** these events for logging purposes.
- **Output**: A cohesive "Session Summary" narrative is appended to `dev-log.md` only after a successful commit.

## 2. Log Schema (`dev-log.md`)
The log utilizes a structured **Markdown/XML** hybrid format for machine readability and human clarity.

**Format Example:**
```xml
  <entry id="evt_commit_a1b2c3d" timestamp="2026-02-01T02:30:00" type="session_summary">
    <commit_hash>a1b2c3d</commit_hash>
    <message>feat: simplified logging</message>
    <assistant_summary>
      You focused on the logging module today, specifically simplifying the `watcher.py` logic. 
      It looks like you successfully disabled the noisy file-event logging and refactored the 
      agent to provide friendly, narrative summaries only when you commit your work.
    </assistant_summary>
  </entry>
```

## 3. Session Logic
- **Implicit Sessions**: A "session" is effectively defined by the work done between commits.
- **Context Window**: The agent analyzes the `git diff` and `git stat` of the commit to understand what files were touched and what was achieved.

## 4. Implementation Details
- **Events**: `on_file_processed` is effectively a no-op for the logger.
- **AI Persona**: The Qwen agent is prompted to act as a "helpful personal assistant," prioritizing intent and outcome over raw technical details.
- **Git Integration**: Relies on `VaultWatcher`'s whitelist of `.git/logs/HEAD`.