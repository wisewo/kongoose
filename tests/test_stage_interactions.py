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
from kongoose.stage import Bike, Player, Stage, StudentCrowd, Turtle
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


def test_student_crowd_repeats_warning_and_active_cycle() -> None:
    stage = make_stage(
        [
            [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
            [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
        ],
        Position(row=1, column=1),
    )
    crowd = StudentCrowd(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.student_crowds.append(crowd)

    stage.update(1.5)
    repeated_warning = stage.update(0.25)
    repeated_active = stage.update(0.25)

    assert repeated_warning == UPDATE_WARNING
    assert repeated_active == UPDATE_STUDENT_CROWD_ACTIVE


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


def test_player_cannot_board_turtle_before_visual_midpoint() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.RIVER, TerrainType.RIVER]],
        Position(row=0, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.0,
        distance_progress=0.49,
    )
    stage.turtles.append(turtle)

    result = stage.move_player(Direction.RIGHT)

    assert result == MOVE_FAILED
    assert stage.failure_reason == FailureReason.FELL_IN_RIVER
    assert stage.player.mounted_turtle is None


def test_player_can_board_turtle_after_visual_midpoint() -> None:
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
    assert stage.player.position == Position(row=0, column=1)


def test_mounted_player_moves_from_turtle_visual_position_to_land() -> None:
    stage = make_stage(
        [
            [TerrainType.RIVER, TerrainType.RIVER, TerrainType.RIVER],
            [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
        ],
        Position(row=0, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.0,
        distance_progress=0.5,
    )
    stage.turtles.append(turtle)
    stage.player.mounted_turtle = turtle

    result = stage.move_player(Direction.DOWN)

    assert result == MOVE_MOVED
    assert stage.player.position == Position(row=1, column=1)
    assert stage.player.mounted_turtle is None


def test_mounted_player_transfers_from_visual_position_to_next_turtle() -> None:
    stage = make_stage(
        [
            [TerrainType.RIVER, TerrainType.RIVER, TerrainType.RIVER],
            [TerrainType.RIVER, TerrainType.RIVER, TerrainType.RIVER],
        ],
        Position(row=0, column=0),
    )
    source = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.0,
        distance_progress=0.5,
    )
    target = Turtle(position=Position(row=1, column=1))
    stage.turtles.extend([source, target])
    stage.player.mounted_turtle = source

    result = stage.move_player(Direction.DOWN)

    assert result == MOVE_MOVED
    assert stage.player.mounted_turtle is target
    assert stage.player.position == Position(row=1, column=1)


def test_stage_update_keeps_mounted_player_on_turtle_grid_position() -> None:
    stage = make_stage(
        [[TerrainType.RIVER, TerrainType.RIVER, TerrainType.RIVER]],
        Position(row=0, column=0),
    )
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.0,
        distance_progress=0.75,
    )
    stage.turtles.append(turtle)
    stage.player.mounted_turtle = turtle

    result = stage.update(0.0)

    assert result == UPDATE_TURTLE_RIDE
    assert stage.player.mounted_turtle is turtle
    assert stage.player.position == Position(row=0, column=0)


def test_turtle_occupies_only_its_current_tile() -> None:
    turtle = Turtle(
        position=Position(row=0, column=0),
        direction=Direction.RIGHT,
        speed=1.0,
        distance_progress=0.5,
    )

    assert turtle.occupies(Position(row=0, column=0))
    assert not turtle.occupies(Position(row=0, column=1))


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


def test_initialize_keeps_repeating_bikes_active_and_resets_positions(
    monkeypatch,
) -> None:
    monkeypatch.setattr("kongoose.stage.random.randrange", lambda _columns: 0)
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
                speed=1.0,
            ),
            Bike(
                position=Position(row=1, column=2),
                direction=Direction.LEFT,
                speed=1.0,
            ),
        ],
    )

    stage.initialize()
    stage.update(1.0)

    stage.initialize()

    assert [bike.position for bike in stage.bikes] == [
        Position(row=1, column=0),
        Position(row=1, column=2),
    ]


def test_initialize_randomizes_bike_start_columns_by_consecutive_row_band(
    monkeypatch,
) -> None:
    offsets = iter([2, 1])
    monkeypatch.setattr(
        "kongoose.stage.random.randrange", lambda _columns: next(offsets)
    )
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START] + [TerrainType.LAND for _column in range(6)],
                [TerrainType.LAND for _column in range(7)],
                [TerrainType.LAND for _column in range(7)],
                [TerrainType.LAND for _column in range(7)],
                [TerrainType.LAND for _column in range(7)],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[
            Bike(Position(row=1, column=0), Direction.RIGHT, 2.0),
            Bike(Position(row=1, column=3), Direction.RIGHT, 2.0),
            Bike(Position(row=2, column=6), Direction.LEFT, 3.0),
            Bike(Position(row=4, column=1), Direction.LEFT, 3.0),
        ],
    )

    stage.initialize()

    assert [(bike.position, bike.speed) for bike in stage.bikes] == [
        (Position(row=1, column=2), 2.0),
        (Position(row=1, column=5), 2.0),
        (Position(row=2, column=1), 3.0),
        (Position(row=4, column=2), 3.0),
    ]


def test_repeating_bikes_can_share_one_row_with_different_columns(monkeypatch) -> None:
    monkeypatch.setattr("kongoose.stage.random.randrange", lambda _columns: 0)
    stage = Stage(
        terrain_map=TerrainMap(
            [
                [TerrainType.START] + [TerrainType.LAND for _column in range(6)],
                [TerrainType.LAND for _column in range(7)],
            ]
        ),
        player=Player(Position(row=0, column=1)),
        bikes=[
            Bike(Position(row=1, column=0), Direction.RIGHT, 2.0),
            Bike(Position(row=1, column=3), Direction.RIGHT, 2.0),
        ],
    )
    stage.initialize()

    result = stage.update(0.5)

    assert result == UPDATE_SAFE
    assert [bike.position for bike in stage.bikes] == [
        Position(row=1, column=1),
        Position(row=1, column=4),
    ]


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

    assert turtle.position == Position(row=0, column=0)


def test_initialize_restores_dynamic_sprite_positions_and_progress(monkeypatch) -> None:
    monkeypatch.setattr("kongoose.stage.random.randrange", lambda _columns: 0)
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
