# AGENTS.md

## Project Overview

This project is a Pygame-based grid movement game.
It is inspired by Crossy Road-style one-tile movement and obstacle avoidance,
but reinterpreted as a fixed-stage campus crossing game starring Geon-goose
(`건구스`).

The first version should remain small and explainable for a team project:
four fixed stages, keyboard movement, obstacle/lake/turtle interactions,
stage result screens, star ratings, saved progress, and basic sound.

## Read Order

When starting implementation work, read these documents first:

1. `doc/02_requirements.md`
2. `doc/06_class_diagram.md`
3. `doc/05_sequence_diagrams.md`
4. `doc/07_stage_balance.md`

Use these documents when behavior, traceability, or domain meaning is unclear:

- `doc/01_use_cases.md`
- `doc/03_domain_model.md`
- `doc/04_system_sequence_diagrams.md`

## Implementation Constraints

- Use Python 3.10+ and Pygame.
- Follow PEP 8 naming:
  - classes use CapWords
  - functions, methods, variables, and attributes use snake_case
  - constants and enum values use UPPER_CASE
- Keep the first implementation scoped to the documented four fixed stages.
- Do not add deferred features unless explicitly requested.
- If implementation needs to diverge from `doc/`, explain the reason before changing behavior.

## Work Style

- Prefer the existing design documents over inventing new behavior.
- Keep each change scoped to one responsibility area.
- Update the relevant `doc/` file when design-level behavior changes.
- Leave a short verification note after implementation work, especially for manual playtest results.
