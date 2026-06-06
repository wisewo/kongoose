from dataclasses import dataclass

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
        self._initial_state = (
            self.position,
            self.direction,
            self.speed,
            self.distance_progress,
            self.is_active,
        )

    def reset(self) -> None:
        (
            self.position,
            self.direction,
            self.speed,
            self.distance_progress,
            self.is_active,
        ) = self._initial_state
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
        if not self.is_active:
            return ()
        return (self.position,)

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
        return (
            self.warning_time
            <= self.elapsed_time
            < (self.warning_time + self.active_duration)
        )

    def occupies(self, position: Position) -> bool:
        return (
            self.is_active()
            and position.row == self.row
            and 0 <= position.column < self.columns
        )


class Turtle(GameSprite):
    def occupies(self, position: Position) -> bool:
        if super().occupies(position):
            return True
        return (
            self.is_active
            and self.distance_progress >= TURTLE_BOARDING_PROGRESS
            and position == self.position.moved(self.direction)
        )


@dataclass
class Player:
    position: Position
    name: str = "건구스"
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


class Stage:
    def __init__(
        self,
        terrain_map: TerrainMap,
        player: Player,
        bikes: list[Bike] | None = None,
        running_crews: list[RunningCrew] | None = None,
        turtles: list[Turtle] | None = None,
        bike_waves_enabled: bool = False,
        max_active_bikes: int | None = None,
        bike_wave_interval: float = 1.0,
        bike_row_cooldown: float | None = None,
        bike_wave_warning_lookahead: float = 1.0,
        bike_wave_batch_size: int = 1,
    ) -> None:
        self.terrain_map = terrain_map
        self.player = player
        self.bikes = [] if bikes is None else bikes
        self.running_crews = [] if running_crews is None else running_crews
        self.turtles = [] if turtles is None else turtles
        self.bike_waves_enabled = bike_waves_enabled
        self.bike_wave_interval = bike_wave_interval
        self.bike_wave_warning_lookahead = bike_wave_warning_lookahead
        self.bike_wave_batch_size = bike_wave_batch_size
        self._bike_wave_timer = 0.0
        self._next_bike_index = 0
        self._warning_bikes: list[Bike] = []
        self.failure_reason: FailureReason | None = None
        self._initial_player_state = (player.position, player.facing_direction)

    def initialize(self) -> None:
        self.failure_reason = None
        self.player.position, self.player.facing_direction = self._initial_player_state
        self.player.leave_turtle()
        for sprite in [*self.bikes, *self.turtles]:
            sprite.reset()
        if self.bike_waves_enabled:
            for bike in self.bikes:
                bike.deactivate()
            self._bike_wave_timer = 0.0
            self._next_bike_index = 0
            self._warning_bikes = []
        for crew in self.running_crews:
            crew.reset()

    def move_player(self, direction: str) -> str:
        self.player.face(direction)
        target_position = self.player.position.moved(direction)
        if not self.terrain_map.can_enter(target_position):
            return MOVE_BLOCKED
        self.player.move_to(target_position)
        self.player.leave_turtle()
        return self.evaluate_player_state()

    def update(self, dt: float) -> str:
        self._tick_bike_wave_timers(dt)
        warning_prepared = self._prepare_bike_wave_warning()
        for sprite in [*self.bikes, *self.running_crews, *self.turtles]:
            sprite.update(dt)
        if self.bike_waves_enabled:
            self._deactivate_offscreen_bikes()
        else:
            self._keep_position_sprites_in_bounds(self.bikes)

        move_result = self.evaluate_player_state()
        if move_result == MOVE_FAILED:
            return UPDATE_FAILED

        self._keep_position_sprites_in_bounds(self.turtles)
        if self.player.mounted_turtle is not None:
            self.player.move_with(self.player.mounted_turtle)

        bike_appeared = self._activate_bike_wave_if_due()
        if bike_appeared or warning_prepared:
            return UPDATE_BIKE_AMBIENCE

        if any(crew.should_warn() for crew in self.running_crews):
            return UPDATE_WARNING

        if any(crew.became_active for crew in self.running_crews):
            return UPDATE_RUNNING_CREW_ACTIVE

        if self.player.mounted_turtle is not None:
            return UPDATE_TURTLE_RIDE

        if not self.bike_waves_enabled and self.bikes:
            return UPDATE_BIKE_AMBIENCE

        return UPDATE_SAFE

    def peek_warning_bike_row(self) -> int | None:
        rows = self.peek_warning_bike_rows()
        if not rows:
            return None
        return rows[0]

    def peek_warning_bike_rows(self) -> tuple[int, ...]:
        return tuple(bike.position.row for bike in self._warning_bikes)

    def evaluate_player_state(self) -> str:
        self.failure_reason = None

        if self.player.mounted_turtle is not None:
            self.player.move_with(self.player.mounted_turtle)
            if not self.terrain_map.can_enter(self.player.position):
                self.failure_reason = FailureReason.CARRIED_OFF_SCREEN
                return MOVE_FAILED

        player_position = self.player.position

        if self._actor_at(self.bikes, player_position) is not None:
            self.player.leave_turtle()
            self.failure_reason = FailureReason.HIT_BIKE
            return MOVE_FAILED

        if self._actor_at(self.running_crews, player_position) is not None:
            self.player.leave_turtle()
            self.failure_reason = FailureReason.HIT_RUNNING_CREW
            return MOVE_FAILED

        terrain = self.terrain_map.get_terrain(player_position)
        if terrain == TerrainType.GOAL:
            self.player.leave_turtle()
            return MOVE_CLEARED

        if terrain == TerrainType.RIVER:
            turtle = self._actor_at(self.turtles, player_position)
            if turtle is None:
                self.player.leave_turtle()
                self.failure_reason = FailureReason.FELL_IN_RIVER
                return MOVE_FAILED
            self.player.ride_turtle(turtle)
            return MOVE_MOVED

        self.player.leave_turtle()
        return MOVE_MOVED

    def _actor_at(self, actors, position: Position):
        return next((actor for actor in actors if actor.occupies(position)), None)

    def _tick_bike_wave_timers(self, dt: float) -> None:
        if not self.bike_waves_enabled:
            return
        self._bike_wave_timer += dt

    def _activate_bike_wave_if_due(self) -> bool:
        if not self.bike_waves_enabled:
            return False
        if self._bike_wave_timer + TIME_EPSILON < self.bike_wave_interval:
            return False

        bikes = self._warning_bikes or self._next_bikes_in_script()
        if not bikes:
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
        if (
            self.bike_wave_warning_lookahead <= TIME_EPSILON
            or self.bike_wave_warning_lookahead + TIME_EPSILON
            >= self.bike_wave_interval
        ):
            return False
        if self._warning_bikes:
            return False

        warning_time = max(
            0.0,
            self.bike_wave_interval - self.bike_wave_warning_lookahead,
        )

        if self._bike_wave_timer + TIME_EPSILON < warning_time:
            return False

        candidates = self._next_bikes_in_script()
        if not candidates:
            return False
        self._warning_bikes = candidates
        return True

    def _deactivate_offscreen_bikes(self) -> None:
        for bike in self.bikes:
            is_offscreen = not 0 <= bike.position.column < self.terrain_map.columns
            if bike.is_active and is_offscreen:
                bike.deactivate()

    def _keep_position_sprites_in_bounds(self, sprites: list[GameSprite]) -> None:
        for sprite in sprites:
            sprite.position = Position(
                row=sprite.position.row,
                column=sprite.position.column % self.terrain_map.columns,
            )
