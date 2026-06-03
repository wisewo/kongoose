# Dynamic Object Bounds C Design

## Goal

Package C prevents dynamic objects from remaining outside valid stage bounds during `Stage.update()`.

## Scope

This change owns `Bike` and `Turtle` movement correction in `Stage`. It does not solve restart initialization (#10), scene layout, sound, or package A rendering defense.

## Design

After dynamic objects update their positions, `Stage` normalizes C-owned actors:

- `Bike` stays on its current row and wraps horizontally within `0 <= column < terrain_map.columns`.
- `Turtle` stays inside the contiguous lake segment on its current row. The turtle head column is wrapped within the valid start columns where every occupied tile remains `TerrainType.LAKE`.

This keeps collision and turtle ride checks working against valid positions while preserving the current one-direction movement model.

## Tests

Add package C tests proving:

- a bike moving past the right edge wraps to column `0`;
- a bike moving past the left edge wraps to the last map column;
- a turtle moving past a lake segment edge wraps so every occupied turtle tile remains on lake terrain.
