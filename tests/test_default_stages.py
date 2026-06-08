import csv
import wave
from pathlib import Path

from kongoose.game import Game
from kongoose.models import TerrainType
from kongoose.scenes import PlayingScene
from kongoose.stage import Stage


def test_default_stage_data_files_are_present() -> None:
    stage_data_dir = Path("data") / "stages"
    expected_files = [
        "stage_1_map.txt",
        "stage_2_map.txt",
        "stage_3_map.txt",
        "stage_4_map.txt",
        "actors.csv",
    ]

    for file_name in expected_files:
        assert (stage_data_dir / file_name).exists()


def test_game_registers_four_default_stages() -> None:
    game = Game()

    assert sorted(game.stages) == [1, 2, 3, 4]
    assert all(isinstance(stage, Stage) for stage in game.stages.values())


def test_selecting_unlocked_stage_uses_real_stage_data() -> None:
    game = Game()

    game.select_stage(1)

    assert game.current_stage is game.stages[1]
    assert isinstance(game.current_scene, PlayingScene)


def test_default_stages_match_documented_balance_shape() -> None:
    game = Game()

    expected_shapes = {
        1: (21, 7),
        2: (35, 8),
        3: (35, 9),
        4: (43, 10),
    }

    for stage_id, (rows, columns) in expected_shapes.items():
        terrain_map = game.stages[stage_id].terrain_map

        assert terrain_map.rows == rows
        assert terrain_map.columns == columns


def test_default_stages_place_start_and_goal_on_documented_tiles() -> None:
    game = Game()

    expected_tiles = {
        1: (_position(20, 3), _position(0, 3)),
        2: (_position(34, 4), _position(0, 4)),
        3: (_position(34, 4), _position(0, 4)),
        4: (_position(42, 5), _position(0, 5)),
    }

    for stage_id, stage in game.stages.items():
        terrain_map = stage.terrain_map
        start_position, goal_position = expected_tiles[stage_id]

        assert stage.player.position == start_position
        assert terrain_map.get_terrain(start_position) == TerrainType.START
        assert terrain_map.get_terrain(goal_position) == TerrainType.GOAL


def test_default_stages_match_documented_object_counts() -> None:
    game = Game()

    assert len(game.stages[1].bikes) == 0
    assert len(game.stages[1].student_crowds) == 0
    assert len(game.stages[1].turtles) == 0

    assert len(game.stages[2].bikes) == 16
    assert len(game.stages[2].student_crowds) == 0
    assert len(game.stages[2].turtles) == 0

    assert len(game.stages[3].bikes) == 0
    assert len(game.stages[3].student_crowds) == 0
    assert len(game.stages[3].turtles) == 54

    assert len(game.stages[4].bikes) == 16
    assert len(game.stages[4].student_crowds) == 3
    assert len(game.stages[4].turtles) == 43


def test_default_stage_bikes_use_precomputed_csv_columns() -> None:
    game = Game()
    bike_rows = [row for row in _actor_rows() if row["type"] == "bike"]
    expected_bikes = {int(row["stage"]): [] for row in bike_rows}

    for row in bike_rows:
        assert row["column"] != ""
        assert row["count"] == ""
        assert row["phase_offset"] == ""
        expected_bikes[int(row["stage"])].append(
            (
                int(row["row"]),
                int(row["column"]),
                row["direction"],
                float(row["speed"]),
            )
        )

    for stage_id, expected in expected_bikes.items():
        actual = [
            (
                bike.position.row,
                bike.position.column,
                bike.direction,
                bike.speed,
            )
            for bike in game.stages[stage_id].bikes
        ]
        assert actual == expected


def test_default_stages_have_required_static_terrain() -> None:
    game = Game()

    expected_walls = {
        1: range(12, 16),
        2: range(15, 19),
        3: range(6, 10),
        4: range(12, 17),
    }
    expected_rivers = {
        1: 0,
        2: 0,
        3: 162,
        4: 140,
    }
    expected_boats = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    }

    for stage_id, stage in game.stages.items():
        terrains = [
            stage.terrain_map.get_terrain(position)
            for position in _all_positions(stage.terrain_map)
        ]

        assert terrains.count(TerrainType.START) == 1
        assert terrains.count(TerrainType.GOAL) == 1
        assert terrains.count(TerrainType.WALL) in expected_walls[stage_id]
        assert terrains.count(_river_type()) == expected_rivers[stage_id]
        assert terrains.count(TerrainType.BOAT) == expected_boats[stage_id]


def test_default_stage_bikes_are_moderate_speed_and_avoid_wall_rows() -> None:
    game = Game()

    expected_minimum_bike_rows = {
        2: 8,
        4: 8,
    }

    for stage_id, minimum_rows in expected_minimum_bike_rows.items():
        stage = game.stages[stage_id]
        bike_rows = {bike.position.row for bike in stage.bikes}

        assert len(bike_rows) >= minimum_rows
        consecutive_rows = {
            row
            for run in _consecutive_runs(sorted(bike_rows))
            if len(run) >= 2
            for row in run
        }
        for bike in stage.bikes:
            row_tiles = [
                stage.terrain_map.get_terrain(_position(bike.position.row, column))
                for column in range(stage.terrain_map.columns)
            ]
            traversal_time = stage.terrain_map.columns / bike.speed

            assert TerrainType.WALL not in row_tiles
            assert _river_type() not in row_tiles
            if bike.position.row in consecutive_rows:
                assert 1.2 <= traversal_time <= 4.0
            else:
                assert 1.2 <= traversal_time <= 1.8


def test_default_stage_bikes_start_repeating_and_spaced_by_row() -> None:
    game = Game()

    for stage_id in (2, 4):
        stage = game.stages[stage_id]

        stage.initialize()

        assert all(bike.position is not None for bike in stage.bikes)
        for bike_row in {bike.position.row for bike in stage.bikes}:
            row_columns = {
                bike.position.column
                for bike in stage.bikes
                if bike.position.row == bike_row
            }
            assert len(row_columns) >= 2


def test_default_stage_bikes_spawn_as_clustered_pairs_by_row() -> None:
    game = Game()

    for stage_id in (2, 4):
        stage = game.stages[stage_id]

        for bike_row in {bike.position.row for bike in stage.bikes}:
            row_columns = sorted(
                bike.position.column
                for bike in stage.bikes
                if bike.position.row == bike_row
            )

            assert _minimum_circular_gap(
                row_columns,
                stage.terrain_map.columns,
            ) == 1


def test_consecutive_bike_row_clusters_are_staggered_by_band() -> None:
    game = Game()

    for stage_id in (2, 4):
        stage = game.stages[stage_id]
        bike_rows = sorted({bike.position.row for bike in stage.bikes})
        for run in _consecutive_runs(bike_rows):
            if len(run) < 2:
                continue
            cluster_starts = [
                _cluster_start(
                    sorted(
                        bike.position.column
                        for bike in stage.bikes
                        if bike.position.row == row
                    )
                )
                for row in run
            ]

            for previous, current in zip(cluster_starts, cluster_starts[1:]):
                assert _minimum_circular_gap(
                    [previous, current],
                    stage.terrain_map.columns,
                ) >= 2


def test_default_stage_bikes_keep_multiple_repeating_bikes_per_row() -> None:
    game = Game()

    for stage_id in (2, 4):
        stage = game.stages[stage_id]
        stage.initialize()

        initial_rows = [bike.position.row for bike in stage.bikes]
        stage.update(1.3)

        updated_rows = [bike.position.row for bike in stage.bikes]
        assert initial_rows == updated_rows
        assert any(initial_rows.count(row) >= 2 for row in set(initial_rows))


def test_stage_2_has_adjacent_bike_row_band() -> None:
    stage = Game().stages[2]
    bike_rows = sorted({bike.position.row for bike in stage.bikes})

    assert _has_adjacent_run(bike_rows)


def test_stage_2_and_4_have_long_bike_row_bands() -> None:
    for stage_id in (2, 4):
        stage = Game().stages[stage_id]
        bike_rows = sorted({bike.position.row for bike in stage.bikes})

        assert any(len(run) >= 3 for run in _consecutive_runs(bike_rows))


def test_stage_2_and_4_reduce_single_bike_rows_with_more_bands() -> None:
    expected_single_row_limits = {
        2: 1,
        4: 0,
    }

    for stage_id, single_row_limit in expected_single_row_limits.items():
        stage = Game().stages[stage_id]
        bike_rows = sorted({bike.position.row for bike in stage.bikes})
        runs = _consecutive_runs(bike_rows)

        assert sum(1 for run in runs if len(run) == 1) <= single_row_limit
        assert sum(1 for run in runs if len(run) >= 2) >= 3


def test_consecutive_bike_row_bands_use_one_lower_speed_per_band() -> None:
    band_speeds: dict[int, list[float]] = {}

    for stage_id in (2, 4):
        stage = Game().stages[stage_id]
        bike_rows = sorted({bike.position.row for bike in stage.bikes})
        for run in _consecutive_runs(bike_rows):
            if len(run) < 2:
                continue
            run_rows = set(run)
            speeds = {
                bike.speed for bike in stage.bikes if bike.position.row in run_rows
            }

            assert len(speeds) == 1
            band_speeds.setdefault(len(run), []).append(next(iter(speeds)))

    assert {2, 3, 4} <= set(band_speeds)
    assert max(band_speeds[2]) <= 4.0
    assert max(band_speeds[3]) <= 3.0
    assert max(band_speeds[4]) <= 2.6
    assert min(band_speeds[2]) > max(band_speeds[3])
    assert min(band_speeds[3]) > max(band_speeds[4])


def test_stage_2_adjacent_bike_rows_are_slower() -> None:
    stage = Game().stages[2]
    adjacent_rows = {13, 14, 15}
    adjacent_bikes = [
        bike for bike in stage.bikes if bike.position.row in adjacent_rows
    ]

    assert len(adjacent_bikes) == 6
    assert {bike.speed for bike in adjacent_bikes} == {3.0}

    two_row_band_rows = {9, 10, 23, 24}
    two_row_band_bikes = [
        bike for bike in stage.bikes if bike.position.row in two_row_band_rows
    ]

    assert len(two_row_band_bikes) == 8
    assert {bike.speed for bike in two_row_band_bikes} == {3.8}


def test_default_stage_rivers_cross_map_and_late_stages_have_adjacent_bands() -> None:
    game = Game()
    river = _river_type()

    for stage_id, stage in game.stages.items():
        river_rows = [
            row
            for row in range(stage.terrain_map.rows)
            if any(
                stage.terrain_map.get_terrain(_position(row, column)) == river
                for column in range(stage.terrain_map.columns)
            )
        ]

        for row in river_rows:
            row_terrains = [
                stage.terrain_map.get_terrain(_position(row, column))
                for column in range(stage.terrain_map.columns)
            ]

            assert set(row_terrains) <= {
                river,
                TerrainType.BOAT,
                TerrainType.START,
                TerrainType.GOAL,
            }
            assert row_terrains.count(river) >= stage.terrain_map.columns - 1
        if stage_id in (3, 4):
            assert _has_adjacent_run(river_rows)


def test_stage_2_is_land_only_obstacle_and_bike_map() -> None:
    game = Game()
    stage = game.stages[2]

    assert (
        _row_terrains(stage, 0)
        == [TerrainType.LAND] * 4 + [TerrainType.GOAL] + [TerrainType.LAND] * 3
    )
    assert (
        _row_terrains(stage, 34)
        == [TerrainType.LAND] * 4 + [TerrainType.START] + [TerrainType.LAND] * 3
    )
    assert len(_turtle_rows(stage)) == 0
    assert all(
        terrain != _river_type()
        for position in _all_positions(stage.terrain_map)
        for terrain in [stage.terrain_map.get_terrain(position)]
    )


def test_stage_3_uses_varied_river_band_lengths_and_land_start() -> None:
    game = Game()
    stage = game.stages[3]

    assert (
        _row_terrains(stage, 34)
        == [TerrainType.LAND] * 4 + [TerrainType.START] + [TerrainType.LAND] * 4
    )
    assert (
        _row_terrains(stage, 0)
        == [TerrainType.LAND] * 4 + [TerrainType.GOAL] + [TerrainType.LAND] * 4
    )

    river_band_lengths = _river_run_lengths(stage)
    assert min(river_band_lengths) == 1
    assert max(river_band_lengths) == 8
    assert set(river_band_lengths) >= {1, 2, 3, 4, 8}


def test_default_turtle_exit_rows_are_empty_full_width_landings() -> None:
    game = Game()

    safe_landing = {TerrainType.LAND, TerrainType.START, TerrainType.GOAL}
    for stage_id in (2, 3, 4):
        stage = game.stages[stage_id]
        turtle_rows = _turtle_rows(stage)
        landing_rows = {
            neighbor_row
            for turtle_row in turtle_rows
            for neighbor_row in (turtle_row - 1, turtle_row + 1)
            if 0 <= neighbor_row < stage.terrain_map.rows
            and neighbor_row not in turtle_rows
        }
        blocked_actor_rows = {bike.position.row for bike in stage.bikes} | {
            crowd.row for crowd in stage.student_crowds
        }

        assert landing_rows.isdisjoint(blocked_actor_rows)
        for row in landing_rows:
            assert set(_row_terrains(stage, row)) <= safe_landing


def test_default_stage_turtles_are_slow_and_stay_on_river_rows() -> None:
    game = Game()
    river = _river_type()

    for stage in game.stages.values():
        for turtle in stage.turtles:
            assert 0.6 <= turtle.speed <= 1.0
            assert stage.terrain_map.get_terrain(turtle.position) == river


def test_default_stage_turtle_rows_use_one_direction_speed_and_clustered_runs() -> None:
    game = Game()

    for stage_id in (3, 4):
        stage = game.stages[stage_id]
        rows = {turtle.position.row for turtle in stage.turtles}

        for turtle_row in rows:
            row_turtles = [
                turtle for turtle in stage.turtles if turtle.position.row == turtle_row
            ]
            columns = sorted(turtle.position.column for turtle in row_turtles)
            directions = {turtle.direction for turtle in row_turtles}
            speeds = {turtle.speed for turtle in row_turtles}

            assert 2 <= len(row_turtles) <= 4
            assert len(directions) == 1
            assert len(speeds) == 1
            assert max(_consecutive_run_lengths(columns)) == len(row_turtles)


def test_stage_4_combines_all_hazard_types_with_multiple_student_crowds() -> None:
    game = Game()
    stage = game.stages[4]

    assert len({bike.position.row for bike in stage.bikes}) >= 8
    assert len({crowd.row for crowd in stage.student_crowds}) >= 2
    assert len(_turtle_rows(stage)) > 0
    assert any(
        stage.terrain_map.get_terrain(position) == _river_type()
        for position in _all_positions(stage.terrain_map)
    )


def test_default_student_crowd_timing_matches_sound_length() -> None:
    game = Game()
    crowds = game.stages[4].student_crowds

    assert len(crowds) >= 2
    for crowd in crowds:
        assert crowd.warning_time == 1.0
        assert crowd.active_duration == _sound_duration("student_crowd.wav") - 1.0


def _all_positions(terrain_map):
    for row in range(terrain_map.rows):
        for column in range(terrain_map.columns):
            yield _position(row, column)


def _has_adjacent_run(rows: list[int], length: int = 2) -> bool:
    return any(all(row + offset in rows for offset in range(length)) for row in rows)


def _consecutive_runs(rows: list[int]) -> list[list[int]]:
    if not rows:
        return []
    runs = [[rows[0]]]
    for row in rows[1:]:
        if row == runs[-1][-1] + 1:
            runs[-1].append(row)
        else:
            runs.append([row])
    return runs


def _river_run_lengths(stage: Stage) -> list[int]:
    river_rows = [
        row
        for row in range(stage.terrain_map.rows)
        if all(terrain == _river_type() for terrain in _row_terrains(stage, row))
    ]
    return _consecutive_run_lengths(river_rows)


def _row_terrains(stage: Stage, row: int) -> list[TerrainType]:
    return [
        stage.terrain_map.get_terrain(_position(row, column))
        for column in range(stage.terrain_map.columns)
    ]


def _turtle_rows(stage: Stage) -> set[int]:
    return {turtle.position.row for turtle in stage.turtles}


def _boat_rows(stage: Stage) -> set[int]:
    return {
        row
        for row in range(stage.terrain_map.rows)
        if TerrainType.BOAT in _row_terrains(stage, row)
    }


def _consecutive_run_lengths(columns: list[int]) -> list[int]:
    if not columns:
        return []
    run_lengths = []
    current_length = 1
    for previous, current in zip(columns, columns[1:]):
        if current == previous + 1:
            current_length += 1
        else:
            run_lengths.append(current_length)
            current_length = 1
    run_lengths.append(current_length)
    return run_lengths


def _minimum_circular_gap(columns: list[int], width: int) -> int:
    return min(
        (current - previous) % width
        for previous, current in zip(columns, columns[1:] + columns[:1])
    )


def _cluster_start(columns: list[int]) -> int:
    return columns[0]


def _position(row: int, column: int):
    from kongoose.models import Position

    return Position(row=row, column=column)


def _actor_rows() -> list[dict[str, str]]:
    actor_path = Path("data") / "stages" / "actors.csv"
    with actor_path.open(newline="", encoding="utf-8") as actor_file:
        return list(csv.DictReader(actor_file))


def _river_type():
    assert hasattr(TerrainType, "RIVER")
    return TerrainType.RIVER


def _sound_duration(file_name: str) -> float:
    sound_path = Path("assets") / "sounds" / file_name
    with wave.open(str(sound_path), "rb") as sound_file:
        return round(sound_file.getnframes() / sound_file.getframerate(), 2)
