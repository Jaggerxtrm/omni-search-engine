---
name: subagent-driven-development
description: Execute implementation plans using subagents for each task, with strict review cycles.
---

# Subagent-Driven Development Skill

Use this skill when executing implementation plans with independent tasks in the current session.

## Core Principle
Fresh subagent per task + two-stage review (spec then quality)

## vs. Executing Plans
-   Same session (no context switch)
-   Fresh subagent per task (no context pollution)
-   Two-stage review after each task
-   Faster iteration

## Process
1.  Read plan, extract all tasks with full text
2.  Create TodoWrite
3.  For each task:
    -   Dispatch implementer subagent
    -   Dispatch spec compliance reviewer
    -   Dispatch code quality reviewer
    -   Mark task complete
4.  Dispatch final code reviewer for entire implementation
5.  Use finishing-a-development-branch

## Red Flags
Skip reviews, proceed with unfixed issues, dispatch multiple implementers in parallel
