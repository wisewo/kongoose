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


def test_stage_update_wraps_bike_that_moves_past_right_edge() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=0),
    )
    bike = Bike(
        position=Position(row=0, column=2),
        direction=Direction.RIGHT,
        speed=1.0,
    )
    stage.bikes.append(bike)

    stage.update(1.0)

    assert bike.position == Position(row=0, column=0)


def test_stage_update_wraps_bike_that_moves_past_left_edge() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.LEFT,
        speed=1.0,
    )
    stage.bikes.append(bike)

    stage.update(1.0)

    assert bike.position == Position(row=0, column=2)


def test_stage_update_keeps_turtle_inside_lake_segment() -> None:
    stage = make_stage(
        [
            [
                TerrainType.START,
                TerrainType.LAND,
                TerrainType.LAKE,
                TerrainType.LAKE,
                TerrainType.LAKE,
                TerrainType.LAND,
            ],
        ],
        Position(row=0, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=3),
        direction=Direction.RIGHT,
        speed=1.0,
        length=2,
    )
    stage.turtles.append(turtle)

    stage.update(1.0)

    assert turtle.positions == (
        Position(row=0, column=2),
        Position(row=0, column=3),
    )
    for position in turtle.positions:
        assert stage.terrain_map.get_terrain(position) is TerrainType.LAKE


def test_initialize_restores_dynamic_sprite_positions_and_progress() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAKE, TerrainType.LAKE, TerrainType.LAKE]],
        Position(row=0, column=0),
    )
    bike = Bike(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.5,
    )
    turtle = Turtle(
        position=Position(row=0, column=1),
        direction=Direction.RIGHT,
        speed=1.5,
        length=2,
    )
    stage.bikes.append(bike)
    stage.turtles.append(turtle)

    bike.update(1.0)
    turtle.update(1.0)
    stage.initialize()

    assert bike.position == Position(row=0, column=0)
    assert bike._distance_progress == 0.0
    assert turtle.position == Position(row=0, column=1)
    assert turtle._distance_progress == 0.0
    assert turtle.positions == (
        Position(row=0, column=1),
        Position(row=0, column=2),
    )


def test_initialize_resets_running_crew_elapsed_time() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    crew = RunningCrew(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.running_crews.append(crew)

    crew.update(0.75)
    stage.initialize()

    assert crew.elapsed_time == 0.0
    assert crew.should_warn()


def test_initialize_dismounts_player_from_turtle() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAKE]],
        Position(row=0, column=1),
    )
    turtle = Turtle(position=Position(row=0, column=1))
    stage.turtles.append(turtle)
    stage.player.ride_turtle(turtle)

    stage.initialize()

    assert stage.player.mounted_turtle is None
