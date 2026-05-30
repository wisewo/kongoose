# Short Stage Balance Design

## Purpose

This document defines the initial stage balance for the Pygame grid-based game.
The project is for coursework, so each stage should be short, readable, and easy
to explain. The first implementation will use four fixed stages instead of
randomly generated maps.

The goal is to make each stage clearable in about 20 to 40 seconds by a player
who understands the controls.

## Chosen Approach

Use four short fixed puzzle stages.

This approach keeps implementation scope small, makes difficulty easier to
control, and gives the project a clear progression:

1. Stage 1 teaches movement and goal arrival.
2. Stage 2 introduces bike obstacles.
3. Stage 3 introduces lake tiles and turtle platforms.
4. Stage 4 combines the learned elements.

Random map generation is intentionally excluded from the first version because
it would make balancing, testing, and explanation harder.

## Stage Defaults

Map size is written as columns x rows in this document. The implementation may
store the same value as rows and columns in `TerrainMap`.

| Stage | Main Goal | Map Size | Main Elements | 3 Stars | 2 Stars | 1 Star |
|---|---|---:|---|---:|---:|---:|
| Stage 1 | Learn movement and goal arrival | 7x7 | 3-5 walls | 20s | 30s | 45s |
| Stage 2 | Avoid bikes | 8x7 | 5-8 walls, 2 bikes | 25s | 38s | 55s |
| Stage 3 | Use turtles to cross lakes | 9x7 | 8-12 lake tiles, 2 turtles | 30s | 45s | 65s |
| Stage 4 | Combined challenge | 10x8 | 8-12 walls, 2 bikes, 1 running crew, 2 turtles | 35s | 52s | 75s |

These numbers are starting values. They should be tuned after playtesting.

## Map Design Rules

Each stage should have one clear intended route from START to GOAL, with small
side spaces for dodging or waiting.

The minimum route length should stay short:

| Stage | Target Minimum Route Length |
|---|---:|
| Stage 1 | 12-18 grid moves |
| Stage 2 | 16-24 grid moves |
| Stage 3 | 20-28 grid moves |
| Stage 4 | 25-35 grid moves |

Walls should guide the player instead of simply filling space. The first version
should keep wall density around 10-15 percent of the map.

Moving obstacles should be limited:

1. Stage 1 has no moving obstacles.
2. Stage 2 has two bike obstacles.
3. Stage 3 has two turtle platforms and no bikes.
4. Stage 4 has two bikes, one running crew event, and two turtle platforms.

The running crew should appear only in Stage 4 in the first version because it
affects a large area and can quickly make a small map feel unfair.

## Star Rating Rule

The default star thresholds are based on a short-stage target:

1. 3 stars: clear time for a clean run with little waiting.
2. 2 stars: about 1.5 times the 3-star time.
3. 1 star: about 2.2 times the 3-star time.

The stage can still be cleared after the 1-star time. The star rating only
records performance.

## Tuning Rules

After implementation, tune the numbers using simple playtest observations:

1. If most first-time players fail before understanding the rule, reduce obstacle
   count or increase safe space.
2. If a stage takes more than 40 seconds on a clean run, shorten the route or
   reduce waiting time.
3. If players can ignore an obstacle, move it closer to the intended route.
4. If a stage feels unfair, add one safe tile before adding more time.
5. If 3 stars require perfect timing, increase the 3-star threshold by 3-5
   seconds.

## Implementation Notes

Stage data should be represented as fixed map definitions. A simple structured
format is enough, such as a list of strings or a nested list of terrain values.

The terrain model should keep using the existing documented concepts:

- LAND
- LAKE
- SAFE
- WALL
- START
- GOAL

Stage-specific entities such as bikes, running crews, and turtles should be
configured separately from static terrain so that map layout and moving behavior
remain easy to adjust independently.

## Out of Scope

The first balanced version will not include:

- random map generation
- more than four stages
- shield or item mechanics
- character customization
- dynamic star thresholds during play

These can be considered after the fixed four-stage version feels complete.
