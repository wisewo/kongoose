from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class TerrainType(Enum):
    LAND = auto()
    LAKE = auto()
    SAFE = auto()
    WALL = auto()
    START = auto()
    GOAL = auto()


class MoveResultType(Enum):
    BLOCKED = auto()
    MOVED = auto()
    CLEARED = auto()
    FAILED = auto()


class StageUpdateResultType(Enum):
    SAFE = auto()
    WARNING = auto()
    TURTLE_RIDE = auto()
    BIKE_AMBIENCE = auto()
    FAILURE = auto()


class FailureReason(Enum):
    HIT_BIKE = auto()
    HIT_RUNNING_CREW = auto()
    FELL_IN_LAKE = auto()
    CARRIED_OFF_SCREEN = auto()


class SoundCue(Enum):
    MOVE = auto()
    TURTLE = auto()
    BIKE_AMBIENCE = auto()
    RUNNING_CREW_WARNING = auto()
    FAILURE = auto()


@dataclass(frozen=True, slots=True)
class Position:
    row: int
    column: int

    def moved(self, direction: Direction) -> Position:
        offsets = {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }
        row_offset, column_offset = offsets[direction]
        return Position(
            row=self.row + row_offset,
            column=self.column + column_offset,
        )
