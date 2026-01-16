---
name: atomic-workflow
description: Enforces atomic project management: SSOT docs in .serena/memories, atomic commits, and sequential changelog updates.
---

# Atomic Workflow Skill

This skill enforces a disciplined, atomic approach to project management, ensuring that every feature is documented, committed, and logged independently.

## When to use this skill

- **Always**. This is the core operating system for this project.
- Use when creating or updating project documentation.
- Use when implementing features or fixing bugs to ensure atomic commits.
- Use when updating the changelog.

## Core Pillars

### 1. SSOT Documentation (Single Source of Truth)

Project documentation lives in `.serena/memories/` and acts as the Single Source of Truth (SSOT).

**Rules:**
- **Atomicity**: Every meaningful feature MUST have its own dedicated document.
- **Naming Convention**: `ssot_<scope>_<name>_<date>.md` (e.g., `ssot_meta_project_overview_2026-01-16.md`).
- **Frontmatter**: Files must strictly follow this YAML frontmatter structure:
  ```yaml
  ---
  title: <Human readable title>
  version: <X.Y.Z>
  updated: <ISO8601 timestamp>
  scope: <project/meta/feature>
  category: <category>
  subcategory: <subcategory>
  domain: [<tag1>, <tag2>]
  changelog:
    - <X.Y.Z> (<YYYY-MM-DD>): <Description of change>
  ---
  ```

### 2. Atomic Commits

Commits must be atomic, meaning they encompass a single logic unit of work.

**Rules:**
- **Trigger**: Commit immediately after completing a roadmap phase, a bugfix, or a feature implementation.
- **Scope**: Do not bundle unrelated changes (e.g., dont mix a bugfix with a formatting change).
- **Message**: Use a descriptive message explaining *what* and *why*.

### 3. Progressive Changelog

The `CHANGELOG.md` tracks the project's evolution in real-time.

**Rules:**
- **Update Frequency**: Update the changelog as part of the atomic unit of work (before the commit).
- **Format**: Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
- **Structure**:
  ```markdown
  ## [X.Y.Z] - YYYY-MM-DD
  
  ### Added
  - Feature A
  
  ### Changed
  - Update B
  
  ### Fixed
  - Bug C
  ```
- **Smart Updates**: Maintain the version history sequentially.
