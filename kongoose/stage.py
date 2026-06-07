from dataclasses import dataclass, field

from kongoose import models
from kongoose.models import Direction, FailureReason, Position, TerrainType
from kongoose.terrain import TerrainMap

TIME_EPSILON = 1e-9
TURTLE_BOARDING_PROGRESS = 0.45


@dataclass
class GameSprite:
    position: Position
    direction: str = Direction.RIGHT
    speed: float = 0.0
    distance_progress: float = 0.0
    is_active: bool = True

    def __post_init__(self) -> None:
        self._initial_state = vars(self).copy()

    def reset(self) -> None:
        self.__dict__.update(self._initial_state)

    def deactivate(self) -> None:
        self.reset()
        self.is_active = False

    def update(self, dt: float) -> None:
        if not self.is_active or self.speed <= 0:
            return
        self.distance_progress += self.speed * dt
        whole_tiles = int(self.distance_progress)
        if whole_tiles == 0:
            return
        for _count in range(whole_tiles):
            self.position = self.position.moved(self.direction)
        self.distance_progress -= whole_tiles

    def get_positions(self) -> tuple[Position, ...]:
        return (self.position,) if self.is_active else ()

    def occupies(self, position: Position) -> bool:
        return position in self.get_positions()


class Bike(GameSprite):
    pass


@dataclass
class BikeLane:
    row: int
    direction: str
    speed: float
    spawn_gap: float
    initial_offset: float = 0.0
    max_active: int = 2
    time_until_spawn: float = 0.0

    def reset(self) -> None:
        self.time_until_spawn = self.initial_offset

    def update(self, dt: float) -> bool:
        self.time_until_spawn -= dt
        if self.time_until_spawn > TIME_EPSILON:
            return False
        self.time_until_spawn += self.spawn_gap
        return True


@dataclass
class StudentCrowd:
    row: int
    columns: int
    warning_time: float
    active_duration: float
    elapsed_time: float = 0.0
    became_active: bool = False

    def update(self, dt: float) -> None:
        was_active = self.is_active()
        self.elapsed_time += dt
        self.became_active = not was_active and self.is_active()

    def reset(self) -> None:
        self.elapsed_time = 0.0
        self.became_active = False

    def should_warn(self) -> bool:
        return self.elapsed_time < self.warning_time

    def is_active(self) -> bool:
        return (
            self.warning_time
            <= self.elapsed_time
            < self.warning_time + self.active_duration
        )

    def occupies(self, position: Position) -> bool:
        return (
            self.is_active()
            and position.row == self.row
            and position.column in range(self.columns)
        )


class Turtle(GameSprite):
    def occupies(self, position: Position) -> bool:
        return super().occupies(position) or (
            self.is_active
            and self.distance_progress >= TURTLE_BOARDING_PROGRESS
            and position == self.position.moved(self.direction)
        )


@dataclass
class Player:
    position: Position
    facing_direction: str = Direction.DOWN
    mounted_turtle: Turtle | None = None


@dataclass
class Stage:
    terrain_map: TerrainMap
    player: Player
    bikes: list[Bike] = field(default_factory=list)
    student_crowds: list[StudentCrowd] = field(default_factory=list)
    turtles: list[Turtle] = field(default_factory=list)
    bike_lanes: list[BikeLane] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.failure_reason: FailureReason | None = None
        self._initial_player_state = (
            self.player.position,
            self.player.facing_direction,
        )

    def initialize(self) -> None:
        self.failure_reason = None
        self.player.position, self.player.facing_direction = self._initial_player_state
        self.player.mounted_turtle = None
        for actor in self.bikes + self.turtles + self.student_crowds:
            actor.reset()
        for lane in self.bike_lanes:
            lane.reset()

    def move_player(self, direction: str) -> str:
        self.player.facing_direction = direction
        target_position = self.player.position.moved(direction)
        if not self.terrain_map.can_enter(target_position):
            return models.MOVE_BLOCKED
        self.player.position = target_position
        self.player.mounted_turtle = None
        return self.evaluate_player_state()

    def update(self, dt: float) -> str:
        for sprite in self.bikes + self.turtles:
            sprite.update(dt)
        for crowd in self.student_crowds:
            crowd.update(dt)
        if self.bike_lanes:
            self._deactivate_offscreen_bikes()
        else:
            self._wrap_position_sprites_in_bounds(self.bikes)
        move_result = self.evaluate_player_state()
        if move_result == models.MOVE_FAILED:
            return models.UPDATE_FAILED
        self._wrap_position_sprites_in_bounds(self.turtles)
        if self.player.mounted_turtle is not None:
            self.player.position = self.player.mounted_turtle.position
        self._update_bike_lanes(dt)
        if any(crowd.should_warn() for crowd in self.student_crowds):
            return models.UPDATE_WARNING
        if any(crowd.became_active for crowd in self.student_crowds):
            return models.UPDATE_STUDENT_CROWD_ACTIVE
        if self.player.mounted_turtle is not None:
            return models.UPDATE_TURTLE_RIDE
        return models.UPDATE_SAFE

    def evaluate_player_state(self) -> str:
        self.failure_reason = None
        if self.player.mounted_turtle is not None:
            self.player.position = self.player.mounted_turtle.position
            if not self.terrain_map.can_enter(self.player.position):
                self.failure_reason = FailureReason.CARRIED_OFF_SCREEN
                return models.MOVE_FAILED
        player_position = self.player.position
        for actors, reason in (
            (self.bikes, FailureReason.HIT_BIKE),
            (self.student_crowds, FailureReason.HIT_STUDENT_CROWD),
        ):
            if self._actor_at(actors, player_position) is not None:
                return self._fail(reason)
        terrain = self.terrain_map.get_terrain(player_position)
        if terrain == TerrainType.GOAL:
            self.player.mounted_turtle = None
            return models.MOVE_CLEARED
        if terrain == TerrainType.RIVER:
            turtle = self._actor_at(self.turtles, player_position)
            if turtle is None:
                return self._fail(FailureReason.FELL_IN_RIVER)
            self.player.mounted_turtle = turtle
            return models.MOVE_MOVED
        self.player.mounted_turtle = None
        return models.MOVE_MOVED

    def _fail(self, reason: FailureReason) -> str:
        self.player.mounted_turtle = None
        self.failure_reason = reason
        return models.MOVE_FAILED

    def _actor_at(self, actors, position: Position):
        return next((actor for actor in actors if actor.occupies(position)), None)

    def _update_bike_lanes(self, dt: float) -> None:
        for lane in self.bike_lanes:
            if lane.update(dt) and self._active_bike_count(lane) < lane.max_active:
                self._activate_bike_from_lane(lane)

    def _active_bike_count(self, lane: BikeLane) -> int:
        return sum(
            1 for bike in self.bikes if bike.is_active and bike.position.row == lane.row
        )

    def _activate_bike_from_lane(self, lane: BikeLane) -> None:
        bike = next(
            bike
            for bike in self.bikes
            if not bike.is_active and bike.position.row == lane.row
        )
        column = (
            0 if lane.direction == Direction.RIGHT else self.terrain_map.columns - 1
        )
        bike.position = Position(lane.row, column)
        bike.direction = lane.direction
        bike.speed = lane.speed
        bike.distance_progress = 0.0
        bike.is_active = True

    def _deactivate_offscreen_bikes(self) -> None:
        columns = self.terrain_map.columns
        for bike in self.bikes:
            if bike.is_active and not 0 <= bike.position.column < columns:
                bike.deactivate()

    def _wrap_position_sprites_in_bounds(self, sprites: list[GameSprite]) -> None:
        for sprite in sprites:
            sprite.position = Position(
                sprite.position.row,
                sprite.position.column % self.terrain_map.columns,
            )
