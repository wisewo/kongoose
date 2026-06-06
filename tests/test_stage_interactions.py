from kongoose.models import (
    MOVE_BLOCKED,
    MOVE_CLEARED,
    MOVE_FAILED,
    MOVE_MOVED,
    UPDATE_FAILED,
    UPDATE_SAFE,
    UPDATE_STUDENT_CROWD_ACTIVE,
    UPDATE_TURTLE_RIDE,
    UPDATE_WARNING,
    Direction,
    FailureReason,
    Position,
    TerrainType,
)
from kongoose.stage import Bike, BikeLane, Player, Stage, StudentCrowd, Turtle
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

    assert result == MOVE_CLEARED


def test_player_faces_last_requested_move_direction() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND]],
        Position(row=0, column=0),
    )

    stage.move_player(Direction.RIGHT)
    blocked_result = stage.move_player(Direction.UP)

    assert stage.player.facing_direction == Direction.UP
    assert blocked_result == MOVE_BLOCKED


def test_player_fails_when_moving_onto_bike() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND]],
        Position(row=0, column=0),
    )
    stage.bikes.append(Bike(position=Position(row=0, column=1)))

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_FAILED
    assert stage.failure_reason == FailureReason.HIT_BIKE


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

    assert result == UPDATE_FAILED
    assert stage.failure_reason == FailureReason.HIT_BIKE


def test_student_crowd_warns_before_active_collision() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    crowd = StudentCrowd(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.student_crowds.append(crowd)

    warning = stage.update(0.25)

    assert warning == UPDATE_WARNING
    assert not crowd.occupies(Position(row=0, column=1))

    failure = stage.update(0.25)

    assert failure == UPDATE_FAILED
    assert stage.failure_reason == FailureReason.HIT_STUDENT_CROWD


def test_student_crowd_reports_active_once_when_warning_ends() -> None:
    stage = make_stage(
        [
            [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
            [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
        ],
        Position(row=1, column=1),
    )
    crowd = StudentCrowd(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.student_crowds.append(crowd)

    warning = stage.update(0.25)
    active = stage.update(0.25)
    still_active = stage.update(0.25)

    assert warning == UPDATE_WARNING
    assert active == UPDATE_STUDENT_CROWD_ACTIVE
    assert still_active != UPDATE_STUDENT_CROWD_ACTIVE


def test_player_fails_on_river_without_turtle() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.RIVER]],
        Position(row=0, column=0),
    )

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_FAILED
    assert stage.failure_reason == FailureReason.FELL_IN_RIVER


def test_turtle_carries_player_after_river_mount() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.RIVER, TerrainType.RIVER]],
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

    assert move_result == MOVE_MOVED
    assert update_result == UPDATE_TURTLE_RIDE
    assert stage.player.mounted_turtle is turtle
    assert stage.player.position == Position(row=0, column=2)


def test_player_can_board_turtle_that_is_mostly_in_next_tile() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.RIVER, TerrainType.RIVER]],
        Position(row=0, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.0,
        distance_progress=0.5,
    )
    stage.turtles.append(turtle)

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_MOVED
    assert stage.player.mounted_turtle is turtle


def test_player_fails_when_turtle_carries_them_off_screen() -> None:
    stage = make_stage(
        [[TerrainType.RIVER, TerrainType.RIVER]],
        Position(row=0, column=1),
    )
    turtle = Turtle(
        position=Position(row=0, column=1),
        direction=Direction.RIGHT,
        speed=1.0,
    )
    stage.turtles.append(turtle)
    stage.player.mounted_turtle = turtle

    result = stage.update(1.0)

    assert result == UPDATE_FAILED
    assert stage.failure_reason == FailureReason.CARRIED_OFF_SCREEN


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


def test_stage_update_does_not_emit_bike_sound_event() -> None:
    stage = make_stage(
        [
            [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
            [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
        ],
        Position(row=1, column=0),
    )
    stage.bikes.append(Bike(position=Position(row=0, column=0)))

    assert stage.update(0.1) == UPDATE_SAFE


def test_bike_lane_stage_starts_with_pool_bikes_inactive() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
                [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[
            Bike(
                position=Position(row=1, column=0),
                direction=Direction.RIGHT,
                speed=0.0,
                is_active=False,
            ),
            Bike(
                position=Position(row=0, column=0),
                direction=Direction.RIGHT,
                speed=9.0,
                is_active=False,
            ),
        ],
        bike_lanes=[
            BikeLane(row=1, direction=Direction.RIGHT, speed=4.0, spawn_gap=0.5),
        ],
    )

    stage.initialize()

    assert {bike.position.row for bike in stage.bikes} == {0, 1}
    assert not any(bike.is_active for bike in stage.bikes)
    assert stage.update(0.49) == UPDATE_SAFE
    assert [bike.position.row for bike in stage.bikes if bike.is_active] == [1]


def test_bike_lanes_spawn_independently_from_offsets() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
                [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
                [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[
            Bike(Position(row=1, column=0), Direction.RIGHT, 4.0, is_active=False),
            Bike(Position(row=2, column=0), Direction.RIGHT, 4.0, is_active=False),
        ],
        bike_lanes=[
            BikeLane(row=1, direction=Direction.RIGHT, speed=4.0, spawn_gap=2.0),
            BikeLane(
                row=2,
                direction=Direction.RIGHT,
                speed=4.0,
                spawn_gap=2.0,
                initial_offset=0.5,
            ),
        ],
    )
    stage.initialize()

    first_update = stage.update(0.1)
    assert first_update == UPDATE_SAFE
    assert [bike.position.row for bike in stage.bikes if bike.is_active] == [1]

    second_update = stage.update(0.4)
    assert second_update == UPDATE_SAFE
    assert {bike.position.row for bike in stage.bikes if bike.is_active} == {1, 2}


def test_bike_lane_can_keep_multiple_bikes_active_in_one_row() -> None:
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START] + [TerrainType.LAND for _column in range(6)],
                [TerrainType.LAND for _column in range(7)],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[
            Bike(Position(row=1, column=0), Direction.RIGHT, 2.0, is_active=False),
            Bike(Position(row=1, column=0), Direction.RIGHT, 2.0, is_active=False),
        ],
        bike_lanes=[
            BikeLane(
                row=1,
                direction=Direction.RIGHT,
                speed=2.0,
                spawn_gap=0.5,
                max_active=2,
            )
        ],
    )
    stage.initialize()

    stage.update(0.1)
    stage.update(0.5)

    active_bikes = [bike for bike in stage.bikes if bike.is_active]
    assert len(active_bikes) == 2
    assert {bike.position.row for bike in active_bikes} == {1}


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


def test_stage_update_wraps_turtle_that_moves_past_right_edge() -> None:
    stage = make_stage(
        [
            [TerrainType.RIVER, TerrainType.RIVER, TerrainType.RIVER],
            [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
        ],
        Position(row=1, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=2),
        direction=Direction.RIGHT,
        speed=1.0,
    )
    stage.turtles.append(turtle)

    stage.update(1.0)

    assert turtle.get_positions() == (Position(row=0, column=0),)


def test_initialize_restores_dynamic_sprite_positions_and_progress() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.RIVER, TerrainType.RIVER, TerrainType.RIVER]],
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
    )
    stage.bikes.append(bike)
    stage.turtles.append(turtle)

    bike.update(1.0)
    turtle.update(1.0)
    stage.initialize()

    assert bike.position == Position(row=0, column=0)
    assert bike.distance_progress == 0.0
    assert turtle.position == Position(row=0, column=1)
    assert turtle.distance_progress == 0.0
    assert turtle.get_positions() == (Position(row=0, column=1),)


def test_initialize_resets_student_crowd_elapsed_time() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    crowd = StudentCrowd(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.student_crowds.append(crowd)

    crowd.update(0.75)
    stage.initialize()

    assert crowd.elapsed_time == 0.0
    assert crowd.should_warn()


def test_initialize_dismounts_player_from_turtle() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.RIVER]],
        Position(row=0, column=1),
    )
    turtle = Turtle(position=Position(row=0, column=1))
    stage.turtles.append(turtle)
    stage.player.mounted_turtle = turtle

    stage.initialize()

    assert stage.player.mounted_turtle is None
