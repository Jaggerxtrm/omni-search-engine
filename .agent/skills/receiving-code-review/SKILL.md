---
name: receiving-code-review
description: Handle code review feedback systematically. Verify before implementing.
---

# Receiving Code Review Skill

Use this skill when receiving code review feedback from any source.

## Core Principle
Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## Response Pattern
1.  READ - Complete feedback without reacting
2.  UNDERSTAND - Restate requirement or ask
3.  VERIFY - Check against codebase reality
4.  EVALUATE - Technically sound for THIS codebase?
5.  RESPOND - Technical acknowledgment or pushback
6.  IMPLEMENT - One item at a time, test each

## Forbidden Responses
-   "You're absolutely right!" (performative)
-   "Great point!" / "Excellent feedback!"
-   "Let me implement that now" (before verification)

## For Unclear Feedback
STOP - do not implement anything. Ask for clarification on unclear items first.

## External Reviewers
-   Check: Technically correct for THIS codebase?
-   Check: Breaks existing functionality?
-   Push back with technical reasoning if wrong

## YAGNI Check
If reviewer suggests "implementing properly": grep codebase for actual usage. If unused → suggest removal.
