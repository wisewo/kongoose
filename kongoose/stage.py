import random
from dataclasses import dataclass, field

from kongoose import models
from kongoose.models import Direction, FailureReason, Position, TerrainType
from kongoose.terrain import TerrainMap

TURTLE_INTERACTION_PROGRESS = 0.5


@dataclass
class GameSprite:
    position: Position
    direction: str = Direction.RIGHT
    speed: float = 0.0
    distance_progress: float = 0.0

    def __post_init__(self) -> None:
        self._initial_state = vars(self).copy()

    def reset(self) -> None:
        self.__dict__.update(self._initial_state)

    def update(self, dt: float) -> None:
        if self.speed <= 0:
            return
        self.distance_progress += self.speed * dt
        whole_tiles = int(self.distance_progress)
        if whole_tiles == 0:
            return
        for _count in range(whole_tiles):
            self.position = self.position.moved(self.direction)
        self.distance_progress -= whole_tiles

    def occupies(self, position: Position) -> bool:
        return self.position == position


class Bike(GameSprite):
    pass


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
        cycle_duration = self.warning_time + self.active_duration
        if self.elapsed_time >= cycle_duration:
            self.elapsed_time %= cycle_duration
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
    def interaction_position(self) -> Position:
        if self.distance_progress >= TURTLE_INTERACTION_PROGRESS:
            return self.position.moved(self.direction)
        return self.position


@dataclass
class Player:
    position: Position
    facing_direction: str = Direction.UP
    mounted_turtle: Turtle | None = None


@dataclass
class Stage:
    terrain_map: TerrainMap
    player: Player
    bikes: list[Bike] = field(default_factory=list)
    student_crowds: list[StudentCrowd] = field(default_factory=list)
    turtles: list[Turtle] = field(default_factory=list)

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
        self._randomize_bike_start_columns()

    def move_player(self, direction: str) -> str:
        self.player.facing_direction = direction
        move_origin = self._player_interaction_position()
        if not self.terrain_map.can_enter(move_origin):
            return self._fail(FailureReason.CARRIED_OFF_SCREEN)
        target_position = move_origin.moved(direction)
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
        self._wrap_position_sprites_in_bounds(self.bikes)
        move_result = self.evaluate_player_state()
        if move_result == models.MOVE_FAILED:
            return models.UPDATE_FAILED
        self._wrap_position_sprites_in_bounds(self.turtles)
        if self.player.mounted_turtle is not None:
            self.player.position = self.player.mounted_turtle.position
        if any(crowd.should_warn() for crowd in self.student_crowds):
            return models.UPDATE_WARNING
        if any(crowd.became_active for crowd in self.student_crowds):
            return models.UPDATE_STUDENT_CROWD_ACTIVE
        if self.player.mounted_turtle is not None:
            return models.UPDATE_TURTLE_RIDE
        return models.UPDATE_SAFE

    def evaluate_player_state(self) -> str:
        self.failure_reason = None
        mounted_turtle = self.player.mounted_turtle
        if mounted_turtle is not None:
            player_position = mounted_turtle.interaction_position()
            if not self.terrain_map.can_enter(player_position):
                self.failure_reason = FailureReason.CARRIED_OFF_SCREEN
                return models.MOVE_FAILED
        else:
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
            turtle = mounted_turtle or self._turtle_at(player_position)
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

    def _turtle_at(self, position: Position) -> Turtle | None:
        return next(
            (
                turtle
                for turtle in self.turtles
                if turtle.interaction_position() == position
            ),
            None,
        )

    def _player_interaction_position(self) -> Position:
        if self.player.mounted_turtle is None:
            return self.player.position
        return self.player.mounted_turtle.interaction_position()

    def _wrap_position_sprites_in_bounds(self, sprites: list[GameSprite]) -> None:
        for sprite in sprites:
            sprite.position = Position(
                sprite.position.row,
                sprite.position.column % self.terrain_map.columns,
            )

    def _randomize_bike_start_columns(self) -> None:
        row_groups: list[list[int]] = []
        for row in sorted({bike.position.row for bike in self.bikes}):
            if not row_groups or row != row_groups[-1][-1] + 1:
                row_groups.append([])
            row_groups[-1].append(row)
        for row_group in row_groups:
            offset = random.randrange(self.terrain_map.columns)
            row_set = set(row_group)
            for bike in self.bikes:
                if bike.position.row in row_set:
                    bike.position = Position(
                        bike.position.row,
                        (bike.position.column + offset) % self.terrain_map.columns,
                    )
