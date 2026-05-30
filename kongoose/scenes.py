from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kongoose.game import Game


class Scene(ABC):
    @abstractmethod
    def enter(self, game: Game) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_event(self, event: object) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, dt: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def draw(self, surface: Any) -> None:
        raise NotImplementedError


class EmptyScene(Scene):
    def __init__(
        self, background_color: tuple[int, int, int] = (242, 247, 241)
    ) -> None:
        self._background_color = background_color

    def enter(self, game: Game) -> None:
        return None

    def handle_event(self, event: object) -> None:
        return None

    def update(self, dt: float) -> None:
        return None

    def draw(self, surface: Any) -> None:
        surface.fill(self._background_color)


class MainScene(EmptyScene):
    pass


class StageSelectScene(EmptyScene):
    pass


class PlayingScene(EmptyScene):
    pass


class FailedScene(EmptyScene):
    pass


class ResultScene(EmptyScene):
    pass
