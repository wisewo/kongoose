# Stage Initialize Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `Stage.initialize()` restore package C dynamic object state.

**Architecture:** Add reset methods at the object level, then have `Stage.initialize()` orchestrate them. Keep player start-position behavior out of scope and preserve the existing mount cleanup.

**Tech Stack:** Python 3.10+, dataclasses, pytest.

---

### Task 1: Dynamic Object Reset

**Files:**
- Modify: `tests/test_stage_interactions.py`
- Modify: `kongoose/stage.py`

- [ ] **Step 1: Write the failing tests**

Add tests that mutate bike, turtle, and running crew state, call `stage.initialize()`, and assert the dynamic state returns to the initial values.

- [ ] **Step 2: Run the targeted tests to verify RED**

Run: `python -m pytest tests/test_stage_interactions.py -q`

Expected: new reset tests fail because `Stage.initialize()` does not restore dynamic object state yet.

- [ ] **Step 3: Implement minimal reset behavior**

Add `GameSprite.__post_init__()`, `GameSprite.reset()`, `RunningCrew.reset()`, and call those methods from `Stage.initialize()`.

- [ ] **Step 4: Run targeted tests to verify GREEN**

Run: `python -m pytest tests/test_stage_interactions.py -q`

Expected: all stage interaction tests pass.

- [ ] **Step 5: Run project verification**

Run: `python -m pytest`

Expected: full test suite passes.
