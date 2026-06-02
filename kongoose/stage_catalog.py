from __future__ import annotations

from collections.abc import Sequence

from kongoose.models import Direction, Position, TerrainType
from kongoose.stage import Bike, Player, RunningCrew, Stage, Turtle
from kongoose.terrain import TerrainMap

TILE_TYPES = {
    ".": TerrainType.LAND,
    "~": TerrainType.LAKE,
    "-": TerrainType.SAFE,
    "#": TerrainType.WALL,
    "S": TerrainType.START,
    "G": TerrainType.GOAL,
}


def build_default_stages() -> dict[int, Stage]:
    return {
        1: _build_stage_one(),
        2: _build_stage_two(),
        3: _build_stage_three(),
        4: _build_stage_four(),
    }


def _build_stage_one() -> Stage:
    return _build_stage(
        [
            "......G",
            ".#.#...",
            "....#..",
            "..#....",
            ".......",
            ".#.....",
            "S......",
        ]
    )


def _build_stage_two() -> Stage:
    return _build_stage(
        [
            ".......G",
            "..#..#..",
            "........",
            ".#....#.",
            "....#...",
            "..#.....",
            "S.......",
        ],
        bikes=[
            Bike(
                position=Position(row=3, column=0),
                direction=Direction.RIGHT,
                speed=1.0,
            ),
            Bike(
                position=Position(row=2, column=7),
                direction=Direction.LEFT,
                speed=1.2,
            ),
        ],
    )


def _build_stage_three() -> Stage:
    return _build_stage(
        [
            "........G",
            "..#..#...",
            ".........",
            "...~~~...",
            "..~~~~~..",
            ".........",
            "S........",
        ],
        turtles=[
            Turtle(
                position=Position(row=3, column=3),
                direction=Direction.RIGHT,
                speed=0.5,
                length=2,
            ),
            Turtle(
                position=Position(row=4, column=2),
                direction=Direction.RIGHT,
                speed=0.4,
                length=3,
            ),
        ],
    )


def _build_stage_four() -> Stage:
    return _build_stage(
        [
            ".........G",
            "..#..#..#.",
            "....#.....",
            "...~~~~...",
            "..~~~~~~..",
            ".#....#...",
            "..#...#...",
            "S.........",
        ],
        bikes=[
            Bike(
                position=Position(row=5, column=0),
                direction=Direction.RIGHT,
                speed=1.2,
            ),
            Bike(
                position=Position(row=2, column=9),
                direction=Direction.LEFT,
                speed=1.5,
            ),
        ],
        running_crews=[
            RunningCrew(
                row=6,
                columns=10,
                warning_time=1.0,
                active_duration=1.0,
            )
        ],
        turtles=[
            Turtle(
                position=Position(row=3, column=3),
                direction=Direction.RIGHT,
                speed=0.6,
                length=2,
            ),
            Turtle(
                position=Position(row=4, column=2),
                direction=Direction.RIGHT,
                speed=0.5,
                length=3,
            ),
        ],
    )


def _build_stage(
    layout: Sequence[str],
    bikes: Sequence[Bike] = (),
    running_crews: Sequence[RunningCrew] = (),
    turtles: Sequence[Turtle] = (),
) -> Stage:
    terrain_rows, start_position = _parse_layout(layout)
    return Stage(
        terrain_map=TerrainMap(terrain_rows),
        player=Player(position=start_position),
        bikes=list(bikes),
        running_crews=list(running_crews),
        turtles=list(turtles),
    )


def _parse_layout(layout: Sequence[str]) -> tuple[list[list[TerrainType]], Position]:
    terrain_rows: list[list[TerrainType]] = []
    start_positions: list[Position] = []

    for row_index, row in enumerate(layout):
        terrain_row: list[TerrainType] = []
        for column_index, tile in enumerate(row):
            terrain_type = TILE_TYPES[tile]
            if terrain_type is TerrainType.START:
                start_positions.append(Position(row=row_index, column=column_index))
            terrain_row.append(terrain_type)
        terrain_rows.append(terrain_row)

    if len(start_positions) != 1:
        raise ValueError("stage layout must contain exactly one START tile")

    return terrain_rows, start_positions[0]
