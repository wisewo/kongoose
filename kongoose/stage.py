from __future__ import annotations

from dataclasses import dataclass, field

from kongoose.models import Direction, FailureReason, Position, TerrainType
from kongoose.results import MoveResult, StageUpdateResult
from kongoose.terrain import TerrainMap


@dataclass(slots=True)
class GameSprite:
    position: Position
    direction: Direction = Direction.RIGHT
    speed: float = 0.0
    _distance_progress: float = 0.0
    _initial_position: Position = field(init=False, repr=False)
    _initial_direction: Direction = field(init=False, repr=False)
    _initial_speed: float = field(init=False, repr=False)
    _initial_distance_progress: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._initial_position = self.position
        self._initial_direction = self.direction
        self._initial_speed = self.speed
        self._initial_distance_progress = self._distance_progress

    def reset(self) -> None:
        self.position = self._initial_position
        self.direction = self._initial_direction
        self.speed = self._initial_speed
        self._distance_progress = self._initial_distance_progress

    def update(self, dt: float) -> None:
        if self.speed <= 0:
            return

        self._distance_progress += self.speed * dt
        whole_tiles = int(self._distance_progress)
        if whole_tiles == 0:
            return

        for _ in range(whole_tiles):
            self.position = self.position.moved(self.direction)
        self._distance_progress -= whole_tiles

    def occupies(self, position: Position) -> bool:
        return position in self.positions

    @property
    def positions(self) -> tuple[Position, ...]:
        return (self.position,)


@dataclass(slots=True)
class Bike(GameSprite):
    pass


@dataclass(slots=True)
class RunningCrew:
    row: int
    columns: int
    warning_time: float
    active_duration: float
    elapsed_time: float = 0.0

    def update(self, dt: float) -> None:
        self.elapsed_time += dt

    def reset(self) -> None:
        self.elapsed_time = 0.0

    def should_warn(self) -> bool:
        return self.elapsed_time < self.warning_time

    def is_active(self) -> bool:
        return self.warning_time <= self.elapsed_time < self.end_time

    def occupies(self, position: Position) -> bool:
        return (
            self.is_active()
            and position.row == self.row
            and 0 <= position.column < self.columns
        )

    @property
    def end_time(self) -> float:
        return self.warning_time + self.active_duration


@dataclass(slots=True)
class Turtle(GameSprite):
    length: int = 1

    @property
    def positions(self) -> tuple[Position, ...]:
        return tuple(
            Position(row=self.position.row, column=self.position.column + offset)
            for offset in range(self.length)
        )

    def carries(self, player: Player) -> bool:
        return player.mounted_turtle is self or self.occupies(player.position)


@dataclass(slots=True)
class Player:
    position: Position
    name: str = "건구스"
    mounted_turtle: Turtle | None = None

    def move_to(self, position: Position) -> None:
        self.position = position

    def move_with(self, turtle: Turtle) -> None:
        self.position = turtle.position

    def ride_turtle(self, turtle: Turtle) -> None:
        self.mounted_turtle = turtle

    def leave_turtle(self) -> None:
        self.mounted_turtle = None


@dataclass(slots=True)
class Stage:
    terrain_map: TerrainMap
    player: Player
    bikes: list[Bike] = field(default_factory=list)
    running_crews: list[RunningCrew] = field(default_factory=list)
    turtles: list[Turtle] = field(default_factory=list)

    def initialize(self) -> None:
        self.player.leave_turtle()
        for sprite in [*self.bikes, *self.turtles]:
            sprite.reset()
        for crew in self.running_crews:
            crew.reset()

    def move_player(self, direction: Direction) -> MoveResult:
        target_position = self.player.position.moved(direction)
        if not self.terrain_map.can_enter(target_position):
            return MoveResult.blocked()
        self.player.move_to(target_position)
        self.player.leave_turtle()
        return self.evaluate_player_state()

    def update(self, dt: float) -> StageUpdateResult:
        for sprite in [*self.bikes, *self.running_crews, *self.turtles]:
            sprite.update(dt)
        self._keep_bikes_in_bounds()

        move_result = self.evaluate_player_state()
        if move_result.is_failed():
            failure_reason = move_result.get_failure_reason()
            if failure_reason is None:
                raise ValueError("failed move result must include a failure reason")
            return StageUpdateResult.failure(failure_reason)

        self._keep_turtles_in_lake_segments()
        if self.player.mounted_turtle is not None:
            self.player.move_with(self.player.mounted_turtle)

        if any(crew.should_warn() for crew in self.running_crews):
            return StageUpdateResult.warning()

        if self.player.mounted_turtle is not None:
            return StageUpdateResult.turtle_ride()

        if self.bikes:
            return StageUpdateResult.bike_ambience()

        return StageUpdateResult.safe()

    def evaluate_player_state(self) -> MoveResult:
        if self.player.mounted_turtle is not None:
            self.player.move_with(self.player.mounted_turtle)
            if not self.terrain_map.can_enter(self.player.position):
                return MoveResult.failed(FailureReason.CARRIED_OFF_SCREEN)

        player_position = self.player.position

        if self._bike_at(player_position) is not None:
            self.player.leave_turtle()
            return MoveResult.failed(FailureReason.HIT_BIKE)

        if self._running_crew_at(player_position) is not None:
            self.player.leave_turtle()
            return MoveResult.failed(FailureReason.HIT_RUNNING_CREW)

        terrain = self.terrain_map.get_terrain(player_position)
        if terrain is TerrainType.GOAL:
            self.player.leave_turtle()
            return MoveResult.cleared()

        if terrain is TerrainType.LAKE:
            turtle = self._turtle_at(player_position)
            if turtle is None:
                self.player.leave_turtle()
                return MoveResult.failed(FailureReason.FELL_IN_LAKE)
            self.player.ride_turtle(turtle)
            return MoveResult.moved()

        self.player.leave_turtle()
        return MoveResult.moved()

    def _bike_at(self, position: Position) -> Bike | None:
        return next((bike for bike in self.bikes if bike.occupies(position)), None)

    def _running_crew_at(self, position: Position) -> RunningCrew | None:
        return next(
            (crew for crew in self.running_crews if crew.occupies(position)),
            None,
        )

    def _turtle_at(self, position: Position) -> Turtle | None:
        return next(
            (turtle for turtle in self.turtles if turtle.occupies(position)),
            None,
        )

    def _keep_bikes_in_bounds(self) -> None:
        for bike in self.bikes:
            bike.position = Position(
                row=bike.position.row,
                column=bike.position.column % self.terrain_map.columns,
            )

    def _keep_turtles_in_lake_segments(self) -> None:
        for turtle in self.turtles:
            self._keep_turtle_in_lake_segment(turtle)

    def _keep_turtle_in_lake_segment(self, turtle: Turtle) -> None:
        lake_segment = self._lake_segment_for_turtle(turtle)
        if lake_segment is None:
            return

        segment_start, segment_end = lake_segment
        max_start = segment_end - turtle.length + 1
        if max_start < segment_start:
            return

        valid_start_count = max_start - segment_start + 1
        column = segment_start + (
            (turtle.position.column - segment_start) % valid_start_count
        )
        turtle.position = Position(row=turtle.position.row, column=column)

    def _lake_segment_for_turtle(self, turtle: Turtle) -> tuple[int, int] | None:
        if not 0 <= turtle.position.row < self.terrain_map.rows:
            return None

        segments = self._lake_segments_on_row(turtle.position.row)
        if not segments:
            return None

        return min(
            segments,
            key=lambda segment: (
                0
                if segment[0] <= turtle.position.column <= segment[1]
                else min(
                    abs(turtle.position.column - segment[0]),
                    abs(turtle.position.column - segment[1]),
                )
            ),
        )

    def _lake_segments_on_row(self, row: int) -> list[tuple[int, int]]:
        segments: list[tuple[int, int]] = []
        segment_start: int | None = None

        for column in range(self.terrain_map.columns):
            terrain = self.terrain_map.get_terrain(Position(row=row, column=column))
            if terrain is TerrainType.LAKE and segment_start is None:
                segment_start = column
            elif terrain is not TerrainType.LAKE and segment_start is not None:
                segments.append((segment_start, column - 1))
                segment_start = None

        if segment_start is not None:
            segments.append((segment_start, self.terrain_map.columns - 1))

        return segments
