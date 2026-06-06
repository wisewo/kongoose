from dataclasses import dataclass
from enum import Enum


class Direction:
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class TerrainType:
    LAND = "."
    RIVER = "~"
    SAFE = "-"
    WALL = "#"
    START = "S"
    GOAL = "G"


class FailureReason(Enum):
    HIT_BIKE = "hit_bike"
    HIT_RUNNING_CREW = "hit_running_crew"
    FELL_IN_RIVER = "fell_in_river"
    CARRIED_OFF_SCREEN = "carried_off_screen"


class SoundCue:
    MOVE_START = "move_start"
    MOVE_SUCCESS = "move_success"
    MOVE = "move"
    BLOCKED = "blocked"
    TURTLE = "turtle"
    BIKE_AMBIENCE = "bike_ambience"
    RUNNING_CREW_WARNING = "running_crew_warning"
    RUNNING_CREW_ACTIVE = "running_crew_active"
    LAKE_SPLASH = "lake_splash"
    FAILURE_SCREEN = "failure_screen"
    CLEAR_SCREEN = "clear_screen"
    UI_SELECT = "ui_select"
    BACKGROUND_MUSIC = "background_music"


MOVE_BLOCKED = "blocked"
MOVE_MOVED = "moved"
MOVE_CLEARED = "cleared"
MOVE_FAILED = "failed"

UPDATE_SAFE = "safe"
UPDATE_WARNING = "warning"
UPDATE_RUNNING_CREW_ACTIVE = "running_crew_active"
UPDATE_TURTLE_RIDE = "turtle_ride"
UPDATE_BIKE_AMBIENCE = "bike_ambience"
UPDATE_FAILED = "failed"


@dataclass
class Position:
    row: int
    column: int

    def moved(self, direction: str) -> "Position":
        offsets = {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }
        row_offset, column_offset = offsets[direction]
        return Position(self.row + row_offset, self.column + column_offset)
