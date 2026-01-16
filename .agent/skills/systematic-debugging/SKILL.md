---
name: systematic-debugging
description: A rigid process for investigating and fixing technical issues. Identify root cause before fixing.
---

# Systematic Debugging Skill

Use this skill for ANY technical issue - test failures, bugs, unexpected behavior, performance problems, build failures.

## Iron Law
`NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST`

## Four Phases

### Phase 1: Root Cause Investigation
-   Read error messages carefully
-   Reproduce consistently
-   Check recent changes
-   Gather evidence in multi-component systems
-   Trace data flow

### Phase 2: Pattern Analysis
-   Find working examples
-   Compare against references
-   Identify differences
-   Understand dependencies

### Phase 3: Hypothesis and Testing
-   Form single hypothesis
-   Test minimally
-   Verify before continuing

### Phase 4: Implementation
-   Create failing test case
-   Implement single fix
-   Verify fix
-   If 3+ fixes failed → Question architecture

## Red Flags
"Quick fix for now", "Just try changing X", proposing solutions before investigation
