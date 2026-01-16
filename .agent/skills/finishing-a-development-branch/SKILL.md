---
name: finishing-a-development-branch
description: Determine next steps when implementation is complete. Merge, PR, or discard.
---

# Finishing a Development Branch Skill

Use this skill when implementation is complete and you need to determine next steps.

## Process
1.  **Verify Tests** - Run test suite, must pass before proceeding
2.  **Determine Base Branch** - `git merge-base HEAD main`
3.  **Present Options:**
    1.  Merge back to base-branch locally
    2.  Push and create a Pull Request
    3.  Keep the branch as-is
    4.  Discard this work
4.  **Execute Choice** - Follow exact steps for each option
5.  **Cleanup Worktree** - For options 1, 2, 4 only

## Red Flags
Proceeding with failing tests, automatic worktree cleanup, no confirmation for discard
