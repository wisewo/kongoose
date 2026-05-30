from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kongoose.models import Direction, Position
from kongoose.results import MoveResult, StageUpdateResult
from kongoose.terrain import TerrainMap


@dataclass(slots=True)
class Player:
    position: Position
    name: str = "건구스"
    mounted_turtle: Any | None = None

    def move_to(self, position: Position) -> None:
        self.position = position

    def move_with(self, turtle: Any) -> None:
        self.position = turtle.position

    def ride_turtle(self, turtle: Any) -> None:
        self.mounted_turtle = turtle

    def leave_turtle(self) -> None:
        self.mounted_turtle = None


@dataclass(slots=True)
class Stage:
    terrain_map: TerrainMap
    player: Player
    bikes: list[Any] = field(default_factory=list)
    running_crews: list[Any] = field(default_factory=list)
    turtles: list[Any] = field(default_factory=list)

    def initialize(self) -> None:
        self.player.leave_turtle()

    def move_player(self, direction: Direction) -> MoveResult:
        target_position = self.player.position.moved(direction)
        if not self.terrain_map.can_enter(target_position):
            return MoveResult.blocked()
        self.player.move_to(target_position)
        return self.evaluate_player_state()

    def update(self, dt: float) -> StageUpdateResult:
        for sprite in [*self.bikes, *self.running_crews, *self.turtles]:
            sprite.update(dt)
        return StageUpdateResult.safe()

    def evaluate_player_state(self) -> MoveResult:
        return MoveResult.moved()
