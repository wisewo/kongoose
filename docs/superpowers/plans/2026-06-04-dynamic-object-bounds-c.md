# Dynamic Object Bounds C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep package C Bike and Turtle objects inside valid movement bounds during stage updates.

**Architecture:** Keep raw tile movement in `GameSprite.update()`. Let `Stage.update()` normalize C-owned dynamic objects after movement because `Stage` has access to `TerrainMap` bounds and terrain types.

**Tech Stack:** Python 3.10+, pytest.

---

### Task 1: C Bounds Tests

**Files:**
- Modify: `tests/test_stage_interactions.py`

- [ ] **Step 1: Write failing tests**

Add tests for bike right-edge wrapping, bike left-edge wrapping, and turtle lake-segment wrapping.

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/test_stage_interactions.py -q`

Expected: the new tests fail because `Stage.update()` currently leaves bikes and turtles outside valid bounds.

### Task 2: Stage Bounds Correction

**Files:**
- Modify: `kongoose/stage.py`

- [ ] **Step 1: Implement minimal helpers**

Add Stage helper methods to wrap bikes by map columns and wrap turtle head positions within contiguous lake segments.

- [ ] **Step 2: Verify GREEN**

Run: `python -m pytest tests/test_stage_interactions.py -q`

Expected: all stage interaction tests pass.

- [ ] **Step 3: Run project checks**

Run:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Expected: tests and lint/format checks pass.
