from __future__ import annotations

from kongoose.models import Direction, FailureReason, Position, TerrainType
from kongoose.results import MoveResultType, StageUpdateResultType
from kongoose.stage import Bike, Player, RunningCrew, Stage, Turtle
from kongoose.terrain import TerrainMap


def make_stage(
    terrain_rows: list[list[TerrainType]],
    player_position: Position,
) -> Stage:
    return Stage(
        terrain_map=TerrainMap(terrain_rows),
        player=Player(position=player_position),
    )


def test_player_clears_stage_by_moving_to_goal() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.GOAL]],
        Position(row=0, column=0),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result.result_type is MoveResultType.CLEARED


def test_player_fails_when_moving_onto_bike() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND]],
        Position(row=0, column=0),
    )
    stage.bikes.append(Bike(position=Position(row=0, column=1)))

    result = stage.move_player(Direction.RIGHT)

    assert result.is_failed()
    assert result.get_failure_reason() is FailureReason.HIT_BIKE


def test_stage_update_fails_when_bike_moves_into_player() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    stage.bikes.append(
        Bike(
            position=Position(row=0, column=0),
            direction=Direction.RIGHT,
            speed=1.0,
        )
    )

    result = stage.update(1.0)

    assert result.is_failure()
    assert result.get_failure_reason() is FailureReason.HIT_BIKE


def test_running_crew_warns_before_active_collision() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    crew = RunningCrew(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.running_crews.append(crew)

    warning = stage.update(0.25)

    assert warning.result_type is StageUpdateResultType.WARNING
    assert not crew.occupies(Position(row=0, column=1))

    failure = stage.update(0.25)

    assert failure.is_failure()
    assert failure.get_failure_reason() is FailureReason.HIT_RUNNING_CREW


def test_player_fails_on_lake_without_turtle() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAKE]],
        Position(row=0, column=0),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result.is_failed()
    assert result.get_failure_reason() is FailureReason.FELL_IN_LAKE


def test_turtle_carries_player_after_lake_mount() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAKE, TerrainType.LAKE]],
        Position(row=0, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=1),
        direction=Direction.RIGHT,
        speed=1.0,
    )
    stage.turtles.append(turtle)

    move_result = stage.move_player(Direction.RIGHT)
    update_result = stage.update(1.0)

    assert move_result.is_moved()
    assert update_result.result_type is StageUpdateResultType.TURTLE_RIDE
    assert stage.player.mounted_turtle is turtle
    assert stage.player.position == Position(row=0, column=2)


def test_player_fails_when_turtle_carries_them_off_screen() -> None:
    stage = make_stage(
        [[TerrainType.LAKE, TerrainType.LAKE]],
        Position(row=0, column=1),
    )
    turtle = Turtle(
        position=Position(row=0, column=1),
        direction=Direction.RIGHT,
        speed=1.0,
    )
    stage.turtles.append(turtle)
    stage.player.ride_turtle(turtle)

    result = stage.update(1.0)

    assert result.is_failure()
    assert result.get_failure_reason() is FailureReason.CARRIED_OFF_SCREEN
