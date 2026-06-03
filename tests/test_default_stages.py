from __future__ import annotations

from kongoose.game import Game
from kongoose.models import TerrainType
from kongoose.scenes import PlayingScene
from kongoose.stage import Stage


def test_game_registers_four_default_stages() -> None:
    game = Game()

    assert sorted(game.stages) == [1, 2, 3, 4]
    assert all(isinstance(stage, Stage) for stage in game.stages.values())


def test_selecting_unlocked_stage_uses_real_stage_data() -> None:
    game = Game()

    game.select_stage(1)

    assert game.current_stage is game.stages[1]
    assert isinstance(game.current_scene, PlayingScene)
    assert game.last_play_message == ""


def test_default_stages_match_documented_balance_shape() -> None:
    game = Game()

    expected_shapes = {
        1: (7, 7),
        2: (7, 8),
        3: (7, 9),
        4: (8, 10),
    }

    for stage_id, (rows, columns) in expected_shapes.items():
        terrain_map = game.stages[stage_id].terrain_map

        assert terrain_map.rows == rows
        assert terrain_map.columns == columns


def test_default_stages_match_documented_object_counts() -> None:
    game = Game()

    assert len(game.stages[1].bikes) == 0
    assert len(game.stages[1].running_crews) == 0
    assert len(game.stages[1].turtles) == 0

    assert len(game.stages[2].bikes) == 2
    assert len(game.stages[2].running_crews) == 0
    assert len(game.stages[2].turtles) == 0

    assert len(game.stages[3].bikes) == 0
    assert len(game.stages[3].running_crews) == 0
    assert len(game.stages[3].turtles) == 2

    assert len(game.stages[4].bikes) == 2
    assert len(game.stages[4].running_crews) == 1
    assert len(game.stages[4].turtles) == 2


def test_default_stages_have_required_static_terrain() -> None:
    game = Game()

    expected_walls = {
        1: range(3, 6),
        2: range(5, 9),
        3: range(0, 10),
        4: range(8, 13),
    }
    expected_lakes = {
        1: range(0, 1),
        2: range(0, 1),
        3: range(8, 13),
        4: range(1, 100),
    }

    for stage_id, stage in game.stages.items():
        terrains = [
            stage.terrain_map.get_terrain(position)
            for position in _all_positions(stage.terrain_map)
        ]

        assert terrains.count(TerrainType.START) == 1
        assert terrains.count(TerrainType.GOAL) == 1
        assert terrains.count(TerrainType.WALL) in expected_walls[stage_id]
        assert terrains.count(TerrainType.LAKE) in expected_lakes[stage_id]


def _all_positions(terrain_map):
    from kongoose.models import Position

    for row in range(terrain_map.rows):
        for column in range(terrain_map.columns):
            yield Position(row=row, column=column)
