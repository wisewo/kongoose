import csv
from pathlib import Path

from kongoose.models import Position
from kongoose.stage import Bike, Player, Stage, StudentCrowd, Turtle
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
        stage_id: {"bikes": [], "student_crowds": [], "turtles": []}
        for stage_id in STAGE_IDS
    }
    with (STAGE_DATA_DIR / "actors.csv").open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            stage_id = int(row["stage"])
            actor_type = row["type"]
            if actor_type == "bike":
                actors[stage_id]["bikes"].append(_bike(row))
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
    return Stage(
        TerrainMap(terrain_rows),
        Player(start_position),
        actors["bikes"],
        actors["student_crowds"],
        actors["turtles"],
    )


def _bike(row: dict) -> Bike:
    return Bike(
        Position(int(row["row"]), int(row["column"])),
        row["direction"],
        float(row["speed"]),
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


def _parse_layout(layout: list[str]) -> tuple[list[list[str]], Position]:
    start_position = next(
        Position(row=row_index, column=column_index)
        for row_index, row in enumerate(layout)
        for column_index, tile in enumerate(row)
        if tile == "S"
    )
    return [list(row) for row in layout], start_position
