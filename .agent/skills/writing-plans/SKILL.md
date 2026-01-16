---
name: writing-plans
description: Write comprehensive implementation plans for features or complex tasks.
---

# Writing Plans Skill

Use this skill when you have a validated design and need to create detailed implementation plans.

## Overview
Write comprehensive plans assuming engineer has zero context for codebase and questionable taste. Document everything: files to touch, code, testing, commands.

## Bite-Sized Task Granularity
Each step is one action (2-5 minutes): write test, run test, implement, verify, commit

## Plan Header (Required)
```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans

**Goal:** [One sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [Key technologies]
```

## Task Structure
- Files: Create/Modify/Test (exact paths)
- Step 1: Write failing test (with code)
- Step 2: Run test to verify fails (command + expected output)
- Step 3: Write minimal implementation (with code)
- Step 4: Run test to verify passes
- Step 5: Commit (with command)

## Save to
`docs/plans/YYYY-MM-DD-<feature-name>.md`
