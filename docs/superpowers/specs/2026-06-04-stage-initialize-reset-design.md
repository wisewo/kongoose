# Stage Initialize Reset Design

## Goal

`Stage.initialize()` restores dynamic stage objects to their start-of-stage state so restart and next-stage flows do not inherit prior movement or timer state.

## Scope

Package C owns dynamic object reset behavior for `Bike`, `RunningCrew`, and `Turtle`.
Player start-position reset is package B coordination work, so this change only keeps the existing player mount cleanup in `Stage.initialize()`.

## Design

`GameSprite` records its construction state in `__post_init__`: position, direction, speed, and movement progress. Its `reset()` method restores those values. Because `Bike` and `Turtle` inherit from `GameSprite`, they get the same reset behavior, including turtle length remaining unchanged.

`RunningCrew` adds a `reset()` method that restores `elapsed_time` to `0.0`. Its row, columns, warning time, and active duration are static stage configuration and remain unchanged.

`Stage.initialize()` calls `player.leave_turtle()` and then resets every bike, running crew, and turtle currently registered on the stage.

## Tests

Add focused tests in `tests/test_stage_interactions.py` proving:

- moving a `Bike` and `Turtle` through `update()` then calling `initialize()` restores their initial positions and clears sprite movement progress;
- advancing a `RunningCrew` then calling `initialize()` resets `elapsed_time`;
- a mounted player is dismounted during initialization.
