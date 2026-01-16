---
name: test-driven-development
description: Enforces TDD methodology: Red, Green, Refactor. No production code without a failing test first.
---

# Test-Driven Development Skill

Use this skill ALWAYS for new features, bug fixes, refactoring, behavior changes.

## Iron Law
`NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST`

## Red-Green-Refactor Cycle

1.  **RED** - Write failing test
    -   One behavior, clear name, real code
    -   Verify it fails correctly

2.  **GREEN** - Minimal code
    -   Simplest code to pass
    -   Verify it passes

3.  **REFACTOR** - Clean up
    -   Remove duplication
    -   Keep tests green

## Why Order Matters
-   Tests-after pass immediately → proves nothing
-   Test-first forces edge case discovery
-   "Tests after achieve same goals" = False

## Red Flags
Code before test, test passes immediately, "I already manually tested it"
