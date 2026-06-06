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
    became_active: bool = False

    def __post_init__(self) -> None:
        self._initial_state = vars(self).copy()

    def reset(self) -> None:
        self.__dict__.update(self._initial_state)
        self.became_active = False

    def activate(self) -> None:
        self.reset()
        self.is_active = True
        self.became_active = True

    def deactivate(self) -> None:
        self.reset()
        self.is_active = False

    def update(self, dt: float) -> None:
        self.became_active = False
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
class RunningCrew:
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
        end_time = self.warning_time + self.active_duration
        return self.warning_time <= self.elapsed_time < end_time

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

    def move_to(self, position: Position) -> None:
        self.position = position

    def face(self, direction: str) -> None:
        self.facing_direction = direction

    def move_with(self, turtle: Turtle) -> None:
        self.position = turtle.position

    def ride_turtle(self, turtle: Turtle) -> None:
        self.mounted_turtle = turtle

    def leave_turtle(self) -> None:
        self.mounted_turtle = None


@dataclass
class Stage:
    terrain_map: TerrainMap
    player: Player
    bikes: list[Bike] = field(default_factory=list)
    running_crews: list[RunningCrew] = field(default_factory=list)
    turtles: list[Turtle] = field(default_factory=list)
    bike_waves_enabled: bool = False
    bike_wave_interval: float = 1.0
    bike_wave_warning_lookahead: float = 1.0
    bike_wave_batch_size: int = 1

    def __post_init__(self) -> None:
        self._bike_wave_timer = 0.0
        self._next_bike_index = 0
        self._warning_bikes: list[Bike] = []
        self.failure_reason: FailureReason | None = None
        self._initial_player_state = (
            self.player.position,
            self.player.facing_direction,
        )

    def initialize(self) -> None:
        self.failure_reason = None
        self.player.position, self.player.facing_direction = self._initial_player_state
        self.player.mounted_turtle = None
        for actor in self.bikes + self.turtles + self.running_crews:
            actor.reset()
        if self.bike_waves_enabled:
            for bike in self.bikes:
                bike.deactivate()
            self._bike_wave_timer = 0.0
            self._next_bike_index = 0
            self._warning_bikes = []

    def move_player(self, direction: str) -> str:
        self.player.facing_direction = direction
        target_position = self.player.position.moved(direction)
        if not self.terrain_map.can_enter(target_position):
            return models.MOVE_BLOCKED
        self.player.position = target_position
        self.player.mounted_turtle = None
        return self.evaluate_player_state()

    def update(self, dt: float) -> str:
        if self.bike_waves_enabled:
            self._bike_wave_timer += dt
        warning_prepared = self._prepare_bike_wave_warning()
        for sprite in self.bikes + self.turtles:
            sprite.update(dt)
        for crew in self.running_crews:
            crew.update(dt)
        if self.bike_waves_enabled:
            self._deactivate_offscreen_bikes()
        else:
            self._keep_position_sprites_in_bounds(self.bikes)
        move_result = self.evaluate_player_state()
        if move_result == models.MOVE_FAILED:
            return models.UPDATE_FAILED
        self._keep_position_sprites_in_bounds(self.turtles)
        if self.player.mounted_turtle is not None:
            self.player.position = self.player.mounted_turtle.position
        bike_appeared = self._activate_bike_wave_if_due()
        if bike_appeared or warning_prepared:
            return models.UPDATE_BIKE_AMBIENCE
        if any(crew.should_warn() for crew in self.running_crews):
            return models.UPDATE_WARNING
        if any(crew.became_active for crew in self.running_crews):
            return models.UPDATE_RUNNING_CREW_ACTIVE
        if self.player.mounted_turtle is not None:
            return models.UPDATE_TURTLE_RIDE
        if not self.bike_waves_enabled and self.bikes:
            return models.UPDATE_BIKE_AMBIENCE
        return models.UPDATE_SAFE

    def peek_warning_bike_row(self) -> int | None:
        return rows[0] if (rows := self.peek_warning_bike_rows()) else None

    def peek_warning_bike_rows(self) -> tuple[int, ...]:
        return tuple(bike.position.row for bike in self._warning_bikes)

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
            (self.running_crews, FailureReason.HIT_RUNNING_CREW),
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

    def _activate_bike_wave_if_due(self) -> bool:
        if not self.bike_waves_enabled or not self.bikes:
            return False
        if self._bike_wave_timer + TIME_EPSILON < self.bike_wave_interval:
            return False
        if not (bikes := self._warning_bikes or self._next_bikes_in_script()):
            return False
        for bike in bikes:
            bike.activate()
        self._warning_bikes = []
        self._bike_wave_timer = 0.0
        self._next_bike_index += len(bikes)
        return True

    def _next_bikes_in_script(self) -> list[Bike]:
        if not self.bikes:
            return []
        batch_size = max(1, min(self.bike_wave_batch_size, len(self.bikes)))
        return [
            self.bikes[(self._next_bike_index + offset) % len(self.bikes)]
            for offset in range(batch_size)
        ]

    def _prepare_bike_wave_warning(self) -> bool:
        lookahead = self.bike_wave_warning_lookahead
        if not self.bike_waves_enabled or not self.bikes or self._warning_bikes:
            return False
        if not TIME_EPSILON < lookahead < self.bike_wave_interval - TIME_EPSILON:
            return False
        warning_time = max(0.0, self.bike_wave_interval - lookahead)
        if self._bike_wave_timer + TIME_EPSILON < warning_time:
            return False
        if not (candidates := self._next_bikes_in_script()):
            return False
        self._warning_bikes = candidates
        return True

    def _deactivate_offscreen_bikes(self) -> None:
        columns = self.terrain_map.columns
        for bike in self.bikes:
            if bike.is_active and not 0 <= bike.position.column < columns:
                bike.deactivate()

    def _keep_position_sprites_in_bounds(self, sprites: list[GameSprite]) -> None:
        for sprite in sprites:
            sprite.position = Position(
                sprite.position.row,
                sprite.position.column % self.terrain_map.columns,
            )
