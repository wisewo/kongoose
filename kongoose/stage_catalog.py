import csv
from pathlib import Path

from kongoose.models import Position
from kongoose.stage import Bike, BikeLane, Player, Stage, StudentCrowd, Turtle
from kongoose.terrain import TerrainMap

STAGE_IDS = range(1, 5)
STAGE_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "stages"
VALID_TILES = set(".~-#SG")


def build_default_stages() -> dict[int, Stage]:
    actors = _load_actors(STAGE_DATA_DIR / "actors.csv")
    return {
        stage_id: _build_stage(
            _load_layout(STAGE_DATA_DIR / f"stage_{stage_id}_map.txt"),
            **actors.get(stage_id, _new_actor_lists()),
        )
        for stage_id in STAGE_IDS
    }


def _load_layout(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").split()


def _load_actors(path: Path) -> dict[int, dict[str, list]]:
    actors: dict[int, dict[str, list]] = {}
    factories = {
        "bike": ("bikes", lambda row: _make_moving_actor(row, Bike)),
        "bike_lane": ("bike_lanes", _make_bike_lane),
        "student_crowd": ("student_crowds", _make_student_crowd),
        "turtle": ("turtles", lambda row: _make_moving_actor(row, Turtle)),
    }
    with path.open(newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            stage_id = _int(row, "stage")
            stage_actors = actors.setdefault(stage_id, _new_actor_lists())
            actor_type = _text(row, "type")
            if actor_type not in factories:
                raise ValueError(f"unknown actor type: {actor_type}")
            actor_list, make_actor = factories[actor_type]
            stage_actors[actor_list].append(make_actor(row))
    return actors


def _new_actor_lists() -> dict[str, list]:
    return {"bikes": [], "bike_lanes": [], "student_crowds": [], "turtles": []}


def _make_moving_actor(row: dict, actor_type):
    return actor_type(
        Position(_int(row, "row"), _int(row, "column")),
        _text(row, "direction"),
        _float(row, "speed"),
    )


def _make_student_crowd(row: dict) -> StudentCrowd:
    return StudentCrowd(
        _int(row, "row"),
        _int(row, "columns"),
        _float(row, "warning_time"),
        _float(row, "active_duration"),
    )


def _make_bike_lane(row: dict) -> BikeLane:
    return BikeLane(
        _int(row, "row"),
        _text(row, "direction"),
        _float(row, "speed"),
        _float(row, "spawn_gap"),
        _float(row, "initial_offset"),
        _int(row, "max_active"),
    )


def _build_stage(
    layout: list[str],
    bikes: list[Bike],
    bike_lanes: list[BikeLane],
    student_crowds: list[StudentCrowd],
    turtles: list[Turtle],
) -> Stage:
    terrain_rows, start_position = _parse_layout(layout)
    columns = len(terrain_rows[0])
    return Stage(
        TerrainMap(terrain_rows),
        Player(start_position),
        bikes + _make_lane_bikes(bike_lanes, columns),
        student_crowds,
        turtles,
        bike_lanes,
    )


def _make_lane_bikes(bike_lanes: list[BikeLane], columns: int) -> list[Bike]:
    bikes = []
    for lane in bike_lanes:
        column = 0 if lane.direction == "right" else columns - 1
        for _count in range(lane.max_active):
            bikes.append(
                Bike(
                    Position(lane.row, column),
                    lane.direction,
                    lane.speed,
                    is_active=False,
                )
            )
    return bikes


def _parse_layout(layout: list[str]) -> tuple[list[list[str]], Position]:
    invalid_tile = next(
        (tile for row in layout for tile in row if tile not in VALID_TILES),
        None,
    )
    if invalid_tile is not None:
        raise ValueError(f"unknown tile type: {invalid_tile}")
    terrain_rows = [list(row) for row in layout]
    start_positions = [
        Position(row=row_index, column=column_index)
        for row_index, row in enumerate(layout)
        for column_index, tile in enumerate(row)
        if tile == "S"
    ]
    if len(start_positions) != 1:
        raise ValueError("stage layout must contain exactly one START tile")
    return terrain_rows, start_positions[0]


def _text(row: dict, name: str) -> str:
    return (row.get(name) or "").strip()


def _int(row: dict, name: str) -> int:
    return int(_text(row, name))


def _float(row: dict, name: str) -> float:
    return float(_text(row, name))
