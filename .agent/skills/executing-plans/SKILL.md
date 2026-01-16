---
name: executing-plans
description: Execute implementation plans in batch mode with checkpoints.
---

# Executing Plans Skill

Use this skill when executing implementation plans in batch mode with checkpoints.

## Core Principle
Batch execution with checkpoints for architect review.

## Process
1.  **Load and Review Plan** - Review critically, raise concerns if any
2.  **Execute Batch** - Default: first 3 tasks, follow each step exactly
3.  **Report** - Show what was implemented + verification output
4.  **Continue** - Apply feedback, execute next batch
5.  **Complete** - Use finishing-a-development-branch

## Stop when
Hit blocker, plan has gaps, don't understand instruction, verification fails
