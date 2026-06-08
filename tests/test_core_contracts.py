import pytest

from kongoose.game import Game
from kongoose.models import (
    MOVE_BLOCKED,
    MOVE_CLEARED,
    MOVE_FAILED,
    MOVE_MOVED,
    UPDATE_FAILED,
    UPDATE_SAFE,
    Direction,
    FailureReason,
    Position,
    TerrainType,
)
from kongoose.stage import Player, Stage, Turtle
from kongoose.terrain import TerrainMap


class DummyScene:
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


def test_terrain_map_allows_river_but_blocks_walls_and_out_of_bounds() -> None:
    terrain_map = TerrainMap(
        [
            [TerrainType.START, TerrainType.LAND, TerrainType.WALL],
            [TerrainType.RIVER, TerrainType.SAFE, TerrainType.BOAT],
        ]
    )

    assert terrain_map.rows == 2
    assert terrain_map.columns == 3
    assert terrain_map.can_enter(Position(row=0, column=1))
    assert terrain_map.can_enter(Position(row=1, column=0))
    assert terrain_map.can_enter(Position(row=1, column=2))
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


def test_result_constants_are_plain_strings() -> None:
    assert MOVE_BLOCKED == "blocked"
    assert MOVE_MOVED == "moved"
    assert MOVE_CLEARED == "cleared"
    assert MOVE_FAILED == "failed"
    assert UPDATE_SAFE == "safe"
    assert UPDATE_FAILED == "failed"


def test_game_changes_scene_and_calls_enter() -> None:
    game = Game()
    scene = DummyScene()

    game.change_scene(scene)

    assert game.current_scene is scene
    assert scene.entered_game is game


def test_game_current_stage_is_derived_from_current_stage_id() -> None:
    first_stage = Stage(
        terrain_map=TerrainMap([[TerrainType.START]]),
        player=Player(Position(row=0, column=0)),
    )
    second_stage = Stage(
        terrain_map=TerrainMap([[TerrainType.GOAL]]),
        player=Player(Position(row=0, column=0)),
    )
    game = Game(stages={1: first_stage, 2: second_stage})

    game.current_stage_id = 2

    assert game.current_stage is second_stage
    with pytest.raises(AttributeError):
        game.current_stage = first_stage


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

    assert wall_result == MOVE_BLOCKED
    assert out_of_bounds_result == MOVE_BLOCKED
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

    assert result == MOVE_MOVED
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

    assert result == MOVE_CLEARED
    assert stage.player.position == Position(row=0, column=1)


def test_stage_reports_river_failure_without_turtle() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.RIVER],
            ]
        ),
        player=Player(Position(row=0, column=0)),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_FAILED
    assert stage.failure_reason == FailureReason.FELL_IN_RIVER
    assert stage.player.position == Position(row=0, column=1)


def test_stage_treats_boat_as_safe_rest_tile() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.BOAT],
            ]
        ),
        player=Player(Position(row=0, column=0)),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_MOVED
    assert stage.failure_reason is None
    assert stage.player.position == Position(row=0, column=1)


def test_stage_manual_move_leaves_mounted_turtle() -> None:
    turtle = Turtle(position=Position(row=0, column=0))
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.LAND],
            ]
        ),
        player=Player(Position(row=0, column=0)),
        turtles=[turtle],
    )
    stage.player.mounted_turtle = turtle

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_MOVED
    assert stage.player.position == Position(row=0, column=1)
    assert stage.player.mounted_turtle is None
