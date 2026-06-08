from dataclasses import dataclass
from enum import Enum


class Direction:
    UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"


class TerrainType:
    LAND, RIVER, SAFE, WALL, START, GOAL, BOAT = (
        ".",
        "~",
        "-",
        "#",
        "S",
        "G",
        "B",
    )


class FailureReason(Enum):
    HIT_BIKE = "hit_bike"
    HIT_STUDENT_CROWD = "hit_student_crowd"
    FELL_IN_RIVER = "fell_in_river"
    CARRIED_OFF_SCREEN = "carried_off_screen"


class SoundCue:
    MOVE_START, MOVE_SUCCESS = "move_start", "move_success"
    BLOCKED, TURTLE, BIKE_AMBIENCE = "blocked", "turtle", "bike_ambience"
    STUDENT_CROWD, WATER_AMBIENCE = "student_crowd", "water_ambience"
    LAKE_SPLASH, FAILURE_SCREEN = "lake_splash", "failure_screen"
    CLEAR_SCREEN, UI_SELECT = "clear_screen", "ui_select"
    BIKE_COLLISION = "bike_collision"
    BACKGROUND_MUSIC = "background_music"


MOVE_BLOCKED, MOVE_MOVED = "blocked", "moved"
MOVE_CLEARED, MOVE_FAILED = "cleared", "failed"
UPDATE_SAFE, UPDATE_WARNING = "safe", "warning"
UPDATE_STUDENT_CROWD_ACTIVE, UPDATE_TURTLE_RIDE = "student_crowd_active", "turtle_ride"
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
