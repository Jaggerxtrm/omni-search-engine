---
name: verification-before-completion
description: Enforces explicit verification steps before claiming a task is done or a bug is fixed.
---

# Verification Before Completion Skill

Use this skill ALWAYS before ANY success/completion claims, commits, PRs, task completion.

## Iron Law
`NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE`

## The Gate Function
1.  IDENTIFY - What command proves this claim?
2.  RUN - Execute the FULL command (fresh, complete)
3.  READ - Full output, check exit code, count failures
4.  VERIFY - Does output confirm the claim?
5.  ONLY THEN - Make the claim

## Common Failures
| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Build succeeds | Build command: exit 0 | Linter passing |
| Bug fixed | Test original symptom: passes | Code changed |

## Red Flags
"Should work", "I'm confident", expressing satisfaction before verification
