---
name: dispatching-parallel-agents
description: Dispatch multiple agents to solve independent problems concurrently.
---

# Dispatching Parallel Agents Skill

Use this skill when you have 3+ independent failures (different test files, different subsystems, different bugs).

## Core Principle
One agent per independent problem domain, working concurrently.

## When to use
-   3+ test files failing with different root causes
-   Each problem can be understood without context from others
-   No shared state between investigations

## Pattern
1.  Identify independent domains
2.  Create focused agent tasks (specific scope, clear goal, constraints)
3.  Dispatch in parallel
4.  Review and integrate

## Don't use when
Failures are related, need full system context, agents would interfere
