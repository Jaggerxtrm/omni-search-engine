---
name: requesting-code-review
description: Dispatch code reviewer subagent with specific context.
---

# Requesting Code Review Skill

Use this skill after each task in subagent-driven development, after major features, before merge.

## Process
1.  Get git SHAs:
    ```bash
    BASE_SHA=$(git rev-parse HEAD~1)
    HEAD_SHA=$(git rev-parse HEAD)
    ```
2.  Dispatch superpowers:code-reviewer subagent with template
3.  Act on feedback:
    -   Fix Critical issues immediately
    -   Fix Important issues before proceeding
    -   Note Minor issues for later
    -   Push back if reviewer is wrong

## Integration
-   **Subagent-Driven Development:** Review after EACH task
-   **Executing Plans:** Review after each batch
-   **Ad-Hoc:** Review before merge or when stuck
