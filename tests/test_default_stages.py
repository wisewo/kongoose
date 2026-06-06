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
        2: (21, 8),
        3: (21, 9),
        4: (24, 10),
    }

    for stage_id, (rows, columns) in expected_shapes.items():
        terrain_map = game.stages[stage_id].terrain_map

        assert terrain_map.rows == rows
        assert terrain_map.columns == columns


def test_default_stages_start_at_bottom_center_and_goal_at_top() -> None:
    game = Game()

    for stage in game.stages.values():
        terrain_map = stage.terrain_map
        center_column = terrain_map.columns // 2

        assert stage.player.position == _position(terrain_map.rows - 1, center_column)
        assert (
            terrain_map.get_terrain(_position(terrain_map.rows - 1, center_column))
            == TerrainType.START
        )
        assert terrain_map.get_terrain(_position(0, center_column)) == TerrainType.GOAL


def test_default_stages_match_documented_object_counts() -> None:
    game = Game()

    assert len(game.stages[1].bikes) == 0
    assert len(game.stages[1].bike_lanes) == 0
    assert len(game.stages[1].student_crowds) == 0
    assert len(game.stages[1].turtles) == 0

    assert len(game.stages[2].bike_lanes) == 8
    assert len(game.stages[2].bikes) == 16
    assert len(game.stages[2].student_crowds) == 0
    assert len(game.stages[2].turtles) == 0

    assert len(game.stages[3].bikes) == 0
    assert len(game.stages[3].bike_lanes) == 0
    assert len(game.stages[3].student_crowds) == 0
    assert len(game.stages[3].turtles) == 3

    assert len(game.stages[4].bike_lanes) == 8
    assert len(game.stages[4].bikes) == 16
    assert len(game.stages[4].student_crowds) == 1
    assert len(game.stages[4].turtles) == 3


def test_default_stages_have_required_static_terrain() -> None:
    game = Game()

    expected_walls = {
        1: range(9, 14),
        2: range(12, 18),
        3: range(6, 13),
        4: range(18, 28),
    }
    expected_rivers = {
        1: 0,
        2: 0,
        3: 27,
        4: 30,
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


def test_default_stage_bike_lanes_are_moderate_speed_and_avoid_wall_rows() -> None:
    game = Game()

    expected_minimum_bike_rows = {
        2: 8,
        4: 8,
    }

    for stage_id, minimum_rows in expected_minimum_bike_rows.items():
        stage = game.stages[stage_id]
        bike_rows = {lane.row for lane in stage.bike_lanes}

        assert len(bike_rows) >= minimum_rows
        for lane in stage.bike_lanes:
            row_tiles = [
                stage.terrain_map.get_terrain(_position(lane.row, column))
                for column in range(stage.terrain_map.columns)
            ]
            traversal_time = stage.terrain_map.columns / lane.speed

            assert TerrainType.WALL not in row_tiles
            assert 1.2 <= traversal_time <= 1.8


def test_default_stage_bike_lanes_use_independent_offsets() -> None:
    game = Game()

    for stage_id in (2, 4):
        stage = game.stages[stage_id]
        lane_offsets = {lane.initial_offset for lane in stage.bike_lanes}

        stage.initialize()

        assert len(lane_offsets) > 1
        assert not any(bike.is_active for bike in stage.bikes)
        stage.update(0.2)
        assert any(bike.is_active for bike in stage.bikes)
        assert sum(1 for bike in stage.bikes if bike.is_active) < len(stage.bikes)


def test_default_stage_bike_lanes_allow_multiple_bikes_per_row() -> None:
    game = Game()

    for stage_id in (2, 4):
        stage = game.stages[stage_id]
        stage.initialize()

        assert all(lane.max_active >= 2 for lane in stage.bike_lanes)
        stage.update(0.1)
        stage.update(1.3)

        active_rows = [bike.position.row for bike in stage.bikes if bike.is_active]
        assert any(active_rows.count(row) >= 2 for row in set(active_rows))


def test_default_stage_rivers_cross_map_and_are_not_adjacent() -> None:
    game = Game()
    river = _river_type()

    for stage in game.stages.values():
        river_rows = [
            row
            for row in range(stage.terrain_map.rows)
            if any(
                stage.terrain_map.get_terrain(_position(row, column)) == river
                for column in range(stage.terrain_map.columns)
            )
        ]

        for row in river_rows:
            assert all(
                stage.terrain_map.get_terrain(_position(row, column)) == river
                for column in range(stage.terrain_map.columns)
            )
            assert row - 1 not in river_rows
            assert row + 1 not in river_rows


def test_default_stage_turtles_are_faster_and_stay_on_river_rows() -> None:
    game = Game()
    river = _river_type()

    for stage in game.stages.values():
        for turtle in stage.turtles:
            assert turtle.speed >= 1.0
            assert stage.terrain_map.get_terrain(turtle.position) == river


def test_default_student_crowd_timing_matches_sound_length() -> None:
    game = Game()
    crowd = game.stages[4].student_crowds[0]

    assert crowd.warning_time == 1.0
    assert crowd.active_duration == _sound_duration("student_crowd.wav") - 1.0


def _all_positions(terrain_map):
    for row in range(terrain_map.rows):
        for column in range(terrain_map.columns):
            yield _position(row, column)


def _position(row: int, column: int):
    from kongoose.models import Position

    return Position(row=row, column=column)


def _river_type():
    assert hasattr(TerrainType, "RIVER")
    return TerrainType.RIVER


def _sound_duration(file_name: str) -> float:
    sound_path = Path("assets") / "sounds" / file_name
    with wave.open(str(sound_path), "rb") as sound_file:
        return round(sound_file.getnframes() / sound_file.getframerate(), 2)
