---
name: using-git-worktrees
description: Use git worktrees for isolated workspaces when starting feature work.
---

# Using Git Worktrees Skill

Use this skill when starting feature work that needs isolation from current workspace.

## Core Principle
Systematic directory selection + safety verification

## Directory Selection Priority
1.  Check existing: `.worktrees/` (preferred, hidden) or `worktrees/`
2.  Check CLAUDE.md for preference
3.  Ask user if neither exists

## Safety Verification
For project-local directories, MUST verify ignored before creating:
```bash
git check-ignore -q .worktrees 2>/dev/null
```
If not ignored: Add to .gitignore + commit immediately

## Creation Steps
1.  Detect project name
2.  Create worktree: `git worktree add $path -b $branch`
3.  Run project setup (npm install, cargo build, etc.)
4.  Verify clean baseline (run tests)
5.  Report location

## Red Flags
Skip ignore verification, assume directory location, proceed with failing tests
