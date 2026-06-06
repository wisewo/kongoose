from kongoose.models import (
    MOVE_BLOCKED,
    MOVE_CLEARED,
    MOVE_FAILED,
    MOVE_MOVED,
    UPDATE_BIKE_AMBIENCE,
    UPDATE_FAILED,
    UPDATE_RUNNING_CREW_ACTIVE,
    UPDATE_SAFE,
    UPDATE_TURTLE_RIDE,
    UPDATE_WARNING,
    Direction,
    FailureReason,
    Position,
    TerrainType,
)
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


def test_running_crew_warns_before_active_collision() -> None:
    stage = make_stage(
        [[TerrainType.START, TerrainType.LAND, TerrainType.LAND]],
        Position(row=0, column=1),
    )
    crew = RunningCrew(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.running_crews.append(crew)

    warning = stage.update(0.25)

    assert warning == UPDATE_WARNING
    assert not crew.occupies(Position(row=0, column=1))

    failure = stage.update(0.25)

    assert failure == UPDATE_FAILED
    assert stage.failure_reason == FailureReason.HIT_RUNNING_CREW


def test_running_crew_reports_active_once_when_warning_ends() -> None:
    stage = make_stage(
        [
            [TerrainType.LAND, TerrainType.LAND, TerrainType.LAND],
            [TerrainType.START, TerrainType.LAND, TerrainType.LAND],
        ],
        Position(row=1, column=1),
    )
    crew = RunningCrew(row=0, columns=3, warning_time=0.5, active_duration=1.0)
    stage.running_crews.append(crew)

    warning = stage.update(0.25)
    active = stage.update(0.25)
    still_active = stage.update(0.25)

    assert warning == UPDATE_WARNING
    assert active == UPDATE_RUNNING_CREW_ACTIVE
    assert still_active != UPDATE_RUNNING_CREW_ACTIVE


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
    stage.player.ride_turtle(turtle)

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


def test_bike_wave_stage_starts_with_candidate_bikes_inactive() -> None:
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
            ),
            Bike(
                position=Position(row=0, column=0),
                direction=Direction.RIGHT,
                speed=9.0,
            ),
        ],
        bike_waves_enabled=True,
        bike_wave_interval=0.5,
    )

    stage.initialize()

    assert {bike.position.row for bike in stage.bikes} == {0, 1}
    assert not any(bike.is_active for bike in stage.bikes)
    assert stage.update(0.49) == UPDATE_SAFE
    assert not any(bike.is_active for bike in stage.bikes)


def test_bike_wave_warns_before_scripted_row_activates() -> None:
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
                speed=9.0,
            )
        ],
        bike_waves_enabled=True,
        bike_wave_interval=2.0,
        bike_wave_warning_lookahead=1.0,
    )
    stage.initialize()

    warning = stage.update(1.0)
    assert warning == UPDATE_BIKE_AMBIENCE
    assert stage.peek_warning_bike_row() == 1

    quiet = stage.update(0.99)
    appeared = stage.update(0.01)

    assert quiet != UPDATE_BIKE_AMBIENCE
    assert appeared == UPDATE_BIKE_AMBIENCE
    assert [bike.position.row for bike in stage.bikes if bike.is_active] == [1]


def test_bike_wave_interval_allows_split_frame_accumulation() -> None:
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
                speed=9.0,
            )
        ],
        bike_waves_enabled=True,
        bike_wave_interval=0.8,
        bike_wave_warning_lookahead=0.0,
    )
    stage.initialize()

    assert stage.update(0.7) == UPDATE_SAFE
    assert stage.update(0.1) == UPDATE_BIKE_AMBIENCE


def test_bike_wave_repeats_scripted_rows_in_data_order() -> None:
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
            Bike(
                position=Position(row=1, column=0),
                direction=Direction.RIGHT,
                speed=9.0,
            ),
            Bike(
                position=Position(row=2, column=0),
                direction=Direction.RIGHT,
                speed=9.0,
            ),
        ],
        bike_waves_enabled=True,
        bike_wave_interval=2.0,
        bike_wave_warning_lookahead=1.0,
    )
    stage.initialize()

    assert stage.update(1.0) == UPDATE_BIKE_AMBIENCE
    assert stage.peek_warning_bike_row() == 1
    assert stage.update(1.0) == UPDATE_BIKE_AMBIENCE
    assert [bike.position.row for bike in stage.bikes if bike.is_active] == [1]

    assert stage.update(1.0) == UPDATE_BIKE_AMBIENCE
    assert stage.peek_warning_bike_row() == 2
    assert stage.update(1.0) == UPDATE_BIKE_AMBIENCE

    active_rows = {bike.position.row for bike in stage.bikes if bike.is_active}

    assert active_rows == {2}


def test_bike_wave_activates_batch_rows_together() -> None:
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
            Bike(Position(row=1, column=0), Direction.RIGHT, 9.0),
            Bike(Position(row=2, column=0), Direction.RIGHT, 9.0),
        ],
        bike_waves_enabled=True,
        bike_wave_interval=2.0,
        bike_wave_warning_lookahead=1.0,
        bike_wave_batch_size=2,
    )
    stage.initialize()

    assert stage.update(1.0) == UPDATE_BIKE_AMBIENCE
    assert stage.peek_warning_bike_rows() == (1, 2)
    assert stage.update(1.0) == UPDATE_BIKE_AMBIENCE
    assert {bike.position.row for bike in stage.bikes if bike.is_active} == {1, 2}


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
        [[TerrainType.START, TerrainType.RIVER]],
        Position(row=0, column=1),
    )
    turtle = Turtle(position=Position(row=0, column=1))
    stage.turtles.append(turtle)
    stage.player.ride_turtle(turtle)

    stage.initialize()

    assert stage.player.mounted_turtle is None
