from dataclasses import dataclass
from enum import Enum


class Direction:
    UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"


class TerrainType:
    LAND, RIVER, SAFE, WALL, START, GOAL = ".", "~", "-", "#", "S", "G"


class FailureReason(Enum):
    HIT_BIKE = "hit_bike"
    HIT_RUNNING_CREW = "hit_running_crew"
    FELL_IN_RIVER = "fell_in_river"
    CARRIED_OFF_SCREEN = "carried_off_screen"


class SoundCue:
    MOVE_START, MOVE_SUCCESS, MOVE = "move_start", "move_success", "move"
    BLOCKED, TURTLE, BIKE_AMBIENCE = "blocked", "turtle", "bike_ambience"
    RUNNING_CREW_WARNING = "running_crew_warning"
    RUNNING_CREW_ACTIVE = "running_crew_active"
    LAKE_SPLASH, FAILURE_SCREEN = "lake_splash", "failure_screen"
    CLEAR_SCREEN, UI_SELECT = "clear_screen", "ui_select"
    BACKGROUND_MUSIC = "background_music"


MOVE_BLOCKED, MOVE_MOVED, MOVE_CLEARED, MOVE_FAILED = (
    "blocked",
    "moved",
    "cleared",
    "failed",
)

UPDATE_SAFE, UPDATE_WARNING = "safe", "warning"
UPDATE_RUNNING_CREW_ACTIVE = "running_crew_active"
UPDATE_TURTLE_RIDE, UPDATE_BIKE_AMBIENCE, UPDATE_FAILED = (
    "turtle_ride",
    "bike_ambience",
    "failed",
)


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
