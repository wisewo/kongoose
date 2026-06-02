from __future__ import annotations

import pytest

from kongoose.game import Game
from kongoose.models import Direction, FailureReason, Position, TerrainType
from kongoose.results import MoveResult, MoveResultType, StageUpdateResult
from kongoose.scenes import Scene
from kongoose.stage import Player, Stage
from kongoose.terrain import TerrainMap


class DummyScene(Scene):
    def __init__(self) -> None:
        self.entered_game = None

    def enter(self, game: Game) -> None:
        self.entered_game = game

    def handle_event(self, event: object) -> None:
        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface: object) -> None:
        return None


def test_position_moves_one_tile_by_direction() -> None:
    position = Position(row=2, column=3)

    assert position.moved(Direction.UP) == Position(row=1, column=3)
    assert position.moved(Direction.DOWN) == Position(row=3, column=3)
    assert position.moved(Direction.LEFT) == Position(row=2, column=2)
    assert position.moved(Direction.RIGHT) == Position(row=2, column=4)


def test_terrain_map_allows_lake_but_blocks_walls_and_out_of_bounds() -> None:
    terrain_map = TerrainMap(
        [
            [TerrainType.START, TerrainType.LAND, TerrainType.WALL],
            [TerrainType.LAKE, TerrainType.SAFE, TerrainType.GOAL],
        ]
    )

    assert terrain_map.rows == 2
    assert terrain_map.columns == 3
    assert terrain_map.can_enter(Position(row=0, column=1))
    assert terrain_map.can_enter(Position(row=1, column=0))
    assert not terrain_map.can_enter(Position(row=0, column=2))
    assert not terrain_map.can_enter(Position(row=-1, column=0))
    assert not terrain_map.can_enter(Position(row=0, column=3))


def test_terrain_map_rejects_jagged_layouts() -> None:
    with pytest.raises(ValueError, match="same number of columns"):
        TerrainMap(
            [
                [TerrainType.START, TerrainType.LAND],
                [TerrainType.GOAL],
            ]
        )


def test_move_result_helpers_report_outcome_and_failure_reason() -> None:
    blocked = MoveResult.blocked()
    moved = MoveResult.moved()
    failed = MoveResult.failed(FailureReason.HIT_BIKE)

    assert blocked.result_type is MoveResultType.BLOCKED
    assert blocked.is_blocked()
    assert moved.is_moved()
    assert failed.is_failed()
    assert failed.get_failure_reason() is FailureReason.HIT_BIKE


def test_stage_update_result_safe_and_failure_helpers() -> None:
    safe = StageUpdateResult.safe()
    failed = StageUpdateResult.failure(FailureReason.FELL_IN_LAKE)

    assert safe.is_safe()
    assert not safe.is_failure()
    assert failed.is_failure()
    assert failed.get_failure_reason() is FailureReason.FELL_IN_LAKE


def test_game_changes_scene_and_calls_enter() -> None:
    game = Game()
    scene = DummyScene()

    game.change_scene(scene)

    assert game.current_scene is scene
    assert scene.entered_game is game


def test_stage_blocks_player_from_walls_and_out_of_bounds() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.WALL],
                [TerrainType.LAND, TerrainType.GOAL],
            ]
        ),
        player=Player(Position(row=0, column=0)),
    )

    wall_result = stage.move_player(Direction.RIGHT)
    out_of_bounds_result = stage.move_player(Direction.UP)

    assert wall_result.is_blocked()
    assert out_of_bounds_result.is_blocked()
    assert stage.player.position == Position(row=0, column=0)


def test_stage_moves_player_one_tile_onto_enterable_terrain() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.LAND],
                [TerrainType.WALL, TerrainType.GOAL],
            ]
        ),
        player=Player(Position(row=0, column=0)),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result.result_type is MoveResultType.MOVED
    assert stage.player.position == Position(row=0, column=1)


def test_stage_reports_clear_when_player_reaches_goal() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.GOAL],
            ]
        ),
        player=Player(Position(row=0, column=0)),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result.is_cleared()
    assert stage.player.position == Position(row=0, column=1)


def test_stage_reports_lake_failure_without_turtle() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.LAKE],
            ]
        ),
        player=Player(Position(row=0, column=0)),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result.is_failed()
    assert result.get_failure_reason() is FailureReason.FELL_IN_LAKE
    assert stage.player.position == Position(row=0, column=1)
