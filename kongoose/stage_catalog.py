import csv
from pathlib import Path

from kongoose.models import Direction, Position
from kongoose.stage import Bike, BikeLane, Player, Stage, StudentCrowd, Turtle
from kongoose.terrain import TerrainMap

STAGE_IDS = (1, 2, 3, 4)
STAGE_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "stages"


def build_default_stages() -> dict[int, Stage]:
    actors = _load_actors()
    return {
        stage_id: _build_stage(stage_id, actors[stage_id]) for stage_id in STAGE_IDS
    }


def _load_actors() -> dict[int, dict[str, list]]:
    actors = {
        stage_id: {"bike_lanes": [], "student_crowds": [], "turtles": []}
        for stage_id in STAGE_IDS
    }
    with (STAGE_DATA_DIR / "actors.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            stage_id = int(row["stage"])
            actor_type = row["type"]
            if actor_type == "bike_lane":
                actors[stage_id]["bike_lanes"].append(_bike_lane(row))
            elif actor_type == "student_crowd":
                actors[stage_id]["student_crowds"].append(_student_crowd(row))
            elif actor_type == "turtle":
                actors[stage_id]["turtles"].append(_turtle(row))
    return actors


def _build_stage(stage_id: int, actors: dict[str, list]) -> Stage:
    layout = (
        (STAGE_DATA_DIR / f"stage_{stage_id}_map.txt")
        .read_text(encoding="utf-8")
        .split()
    )
    terrain_rows, start_position = _parse_layout(layout)
    bike_lanes = actors["bike_lanes"]
    return Stage(
        TerrainMap(terrain_rows),
        Player(start_position),
        _make_lane_bikes(bike_lanes, len(terrain_rows[0])),
        actors["student_crowds"],
        actors["turtles"],
        bike_lanes,
    )


def _bike_lane(row: dict) -> BikeLane:
    return BikeLane(
        int(row["row"]),
        row["direction"],
        float(row["speed"]),
        float(row["spawn_gap"]),
        float(row["initial_offset"]),
        int(row["max_active"]),
    )


def _student_crowd(row: dict) -> StudentCrowd:
    return StudentCrowd(
        int(row["row"]),
        int(row["columns"]),
        float(row["warning_time"]),
        float(row["active_duration"]),
    )


def _turtle(row: dict) -> Turtle:
    return Turtle(
        Position(int(row["row"]), int(row["column"])),
        row["direction"],
        float(row["speed"]),
    )


def _make_lane_bikes(bike_lanes: list[BikeLane], columns: int) -> list[Bike]:
    bikes = []
    for lane in bike_lanes:
        column = 0 if lane.direction == Direction.RIGHT else columns - 1
        bikes.extend(
            Bike(
                Position(lane.row, column),
                lane.direction,
                lane.speed,
                is_active=False,
            )
            for _count in range(lane.max_active)
        )
    return bikes


def _parse_layout(layout: list[str]) -> tuple[list[list[str]], Position]:
    start_position = next(
        Position(row=row_index, column=column_index)
        for row_index, row in enumerate(layout)
        for column_index, tile in enumerate(row)
        if tile == "S"
    )
    return [list(row) for row in layout], start_position
